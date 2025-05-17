#include <llvm/IR/Instructions.h>
#include <llvm/IR/Function.h>
#include <llvm/IR/InstIterator.h>
#include <llvm/IR/LegacyPassManager.h>

#include "PointerAnalysis.h"

/// Alias types used to do pointer analysis.
#define MUST_ALIAS

bool PointerAnalysisPass::doInitialization(Module *M) {
	return false;
}

bool PointerAnalysisPass::doFinalization(Module *M) {
	return false;
}

Value *PointerAnalysisPass::getSourcePointer(Value *P) {
	// 追踪指针的source，主要追踪以下四种类型的指针：
	// 函数参数、栈分配、函数调用返回、全局变量
	Value *SrcP = P;
	Instruction *SrcI = dyn_cast<Instruction>(SrcP);
	
	std::list<Value *> EI;

	EI.push_back(SrcP);
	while (!EI.empty()) {
		Value *TI = EI.front();
		EI.pop_front();

		// Possible sources
		if (isa<Argument>(TI)
				|| isa<AllocaInst>(TI)
				|| isa<CallInst>(TI)
				|| isa<GlobalVariable>(TI)
		   )
			return SrcP;
		
		// 处理一元指令（譬如类型转换指令）
		if (UnaryInstruction *UI = dyn_cast<UnaryInstruction>(TI)) {
			// 获取一元指令的操作数
			Value *UO = UI->getOperand(0);
			// 如果操作数是指针类型且是指令，将操作数假如追踪队列
			if (UO->getType()->isPointerTy() && isa<Instruction>(UO)) {
				SrcP = UO;
				EI.push_back(SrcP);
			}
		}
		// 处理结构体/数组成员访问指令
		else if (GetElementPtrInst *GEP = dyn_cast<GetElementPtrInst>(TI)) {
			SrcP = GEP->getPointerOperand();
			EI.push_back(SrcP);
		}
	}

	return SrcP;
}

void PointerAnalysisPass::augmentMustAlias(Function *F, Value *P, 
		set<Value *> &ASet) {

	std::set<Value *> PV;
	std::list<Value *> EV;

	EV.push_back(P);
	while (!EV.empty()) {
		Value *TV = EV.front();
		EV.pop_front();
		if (PV.count(TV) != 0)
			continue;
		PV.insert(TV);

		if (GetElementPtrInst *GEP = dyn_cast<GetElementPtrInst>(TV)) {
			EV.push_back(GEP->getPointerOperand());
			continue;
		}
		if (CastInst *CI = dyn_cast<CastInst>(TV)) {
			EV.push_back(CI->getOperand(0));
			continue;
		}
		if (AllocaInst *AI = dyn_cast<AllocaInst>(TV)) {
			EV.push_back(AI);
			continue;
		}
	}

	for (auto V : PV) {
		ASet.insert(V);
		for (auto U : V->users()) {
			if (isa<GetElementPtrInst>(U)) 
				ASet.insert(U);
			else if (isa<CastInst>(U))
				ASet.insert(U);
		}
	}
}

// 疑似是个废函数
/// Collect all interesting pointers 
void PointerAnalysisPass::collectPointers(Function *F, 
		set<Value *> &PSet) {

	// Scan instructions to extract all pointers.
	for (inst_iterator i = inst_begin(F), ei = inst_end(F);
			i != ei; ++i) {

		Instruction *I = dyn_cast<Instruction>(&*i);
		if (!(I->getType()->isPointerTy()))
			continue;

		if (isa<LoadInst>(I)
				|| isa<GetElementPtrInst>(I)
				|| isa<CastInst>(I)
		   )
			PSet.insert(I);
	}
}

// 检测函数中存在的别名情况
// Detect aliased pointers in this function.
void PointerAnalysisPass::detectAliasPointers(Function *F,
		AAResults &AAR,
		PointerAnalysisMap &aliasPtrs) {

	std::set<Value *> addr1Set;
	std::set<Value *> addr2Set;
	Value *Addr1, *Addr2;

	// Collect interesting pointers
	for (inst_iterator i = inst_begin(F), ei = inst_end(F);
			i != ei; ++i) {

		Instruction *I = dyn_cast<Instruction>(&*i);

		if (LoadInst *LI = dyn_cast<LoadInst>(I)) {
			// 处理Load指令的操作数指针
			addr1Set.insert(LI->getPointerOperand());
		}
		else if (StoreInst *SI = dyn_cast<StoreInst>(I)) {
			// 处理Store指令的操作数指针
			addr1Set.insert(SI->getPointerOperand());
		}
		else if ( CallInst *CI = dyn_cast<CallInst>(I)) {
			for (unsigned j = 0, ej = CI->getNumArgOperands();
					j < ej; ++j) {
				Value *Arg = CI->getArgOperand(j);
				if (!Arg->getType()->isPointerTy())
					continue;
				addr1Set.insert(Arg);
			}
		}
	}

	// 如果分析的指针数量太多就不分析了，要不会卡死
	// FIXME: avoid being stuck
	if (addr1Set.size() > 1200) {
		return;
	}

	// 接下来进行同名分析
	for (auto Addr1 : addr1Set) {
		for (auto Addr2 : addr1Set) {
			// 如果指的是同一个地址，跳过
			if (Addr1 == Addr2)
				continue;
			// 别名分析
			AliasResult AResult = AAR.alias(Addr1, Addr2);

			bool notAlias = true;
			// 别名分为必然别名，部分别名，可能别名，无别名四种。对于前两种，我们认为是别名。
			if (AResult == llvm::AliasResult::MustAlias || AResult == llvm::AliasResult::PartialAlias)
				notAlias = false;
			// 对于可能别名，我们检查他们各自的指向地址，如果相同则也认为是别名。（默认配置项MUST_ALIAS是打开的）
			else if (AResult == llvm::AliasResult::MayAlias) {
#ifdef MUST_ALIAS
				if (getSourcePointer(Addr1) == getSourcePointer(Addr2))
					notAlias = false;
#else
				notAlias = false;
#endif
			}
			// 不是别名，不分析了。
			if (notAlias)
				continue;
			// 将别名关系加入到别名分析的Map容器aliasPtr中
			auto as = aliasPtrs.find(Addr1);
			// 如果Addr1不在aliasPtrs中，就新建一个set，然后插入到aliasPtrs中
			if (as == aliasPtrs.end()) {
				SmallPtrSet<Value *, 16> sv;
				sv.insert(Addr2);
				aliasPtrs[Addr1] = sv;
			} 
			else {
			// 如果Addr1在aliasPtrs中，就直接插入到set中
				as->second.insert(Addr2);
			}
		}
	}
}

bool PointerAnalysisPass::doModulePass(Module *M) {

	// Save TargetLibraryInfo.
	Triple ModuleTriple(M->getTargetTriple());
	TargetLibraryInfoImpl TLII(ModuleTriple);
	TLI = new TargetLibraryInfo(TLII);

	// Run BasicAliasAnalysis pass on each function in this module.
	// XXX: more complicated alias analyses may be required.
	legacy::FunctionPassManager *FPasses = new legacy::FunctionPassManager(M);
	AAResultsWrapperPass *AARPass = new AAResultsWrapperPass();

	FPasses->add(AARPass);

	FPasses->doInitialization();
	for (Function &F : *M) {
		if (F.isDeclaration())
			continue;
		FPasses->run(F);
	}
	FPasses->doFinalization();

	// 别名分析。
	// Basic alias analysis result.
	AAResults &AAR = AARPass->getAAResults();

	// 开始对模块中的每一个函数做别名分析
	for (Module::iterator f = M->begin(), fe = M->end();
			f != fe; ++f) {
		Function *F = &*f;
		// 别名分析的Map容器
		PointerAnalysisMap aliasPtrs;

		if (F->empty())
			continue;

		// 监测函数中是否有别名指针
		detectAliasPointers(F, AAR, aliasPtrs);

		// Save pointer analysis result.
		Ctx->FuncPAResults[F] = aliasPtrs;
		Ctx->FuncAAResults[F] = &AAR;
	}

	return false;
}