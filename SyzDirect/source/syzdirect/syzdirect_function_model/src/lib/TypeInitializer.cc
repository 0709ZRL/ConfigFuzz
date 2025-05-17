#include <llvm/IR/Instructions.h>
#include <llvm/IR/Function.h>
#include <llvm/IR/InstIterator.h>
#include <llvm/IR/DebugInfo.h>

#include "TypeInitializer.h"
#include "Common.h"

// 这三个map的用处是：
// type* -> global value name -> type name
// 构建type* -> type name的映射

// 类型指针到全局值名称的映射
// map type* to global value name
map<Type*, string> TypeValueMap;

// 全局值名称到类型名称的映射
// map global value name to type name
map<string,string> VnameToTypenameMap;

// 类型指针到类型名称的映射
map<Type*, string> TypeToTNameMap;

bool TypeInitializerPass::doInitialization(Module *M) {
	// 初始化TypeValueMap
	// 将每个没有类型名称的全局结构体映射到其值名称
	// Initializing TypeValueMap
	// Map every gloable struct wihout type name to their
	// value name
	for(Module::global_iterator gi = M->global_begin(),
			ge = M->global_end(); gi != ge; ++gi) {
		GlobalValue *GV = &*gi;
		Type *GVTy = GV->getValueType();
		string Vname = static_cast<string>(GV->getName());
		// 处理没名字的结构体类型
		if (StructType *GVSTy = dyn_cast<StructType>(GVTy)) {
			if(GVSTy->hasName())
				continue;
			TypeValueMap.insert(pair<Type*, string>(GVTy,Vname));
		}
	}

	// 初始化StructTNMap
	// 构建变量名到类型名的映射
	// Initializing StructTNMap
	// Map global variable name to their struct type name
	for (Module::iterator ff = M->begin(),
			MEnd = M->end();ff != MEnd; ++ff) {
		// 遍历模块中的每个函数
		Function *Func = &*ff;
		// 如果是内建函数则跳过
		if (Func->isIntrinsic())
			continue;
		// 遍历函数中的每个指令
		for (inst_iterator ii = inst_begin(Func), e = inst_end(Func);
					ii != e; ++ii) {
			Instruction *Inst = &*ii;
			// 遍历指令中的每个操作数
			unsigned T = Inst->getNumOperands();
			for(int i = 0; i < T; i++) {
				Value *VI = Inst->getOperand(i);
				if (!VI)
					continue;
				if (!VI->hasName())
					continue;
				// 获取操作数类型
				Type *VT = VI->getType();
				// 如果是指针类型则获取指针元素类型
				while(VT && VT->isPointerTy())
					// 获取指针类型的元素类型
					// (之所以用while是因为不止一个？不确定)
					VT = VT->getPointerElementType();
				if (!VT)
					continue;

				// 如果是结构体类型则获取结构体名称
				if (StructType *SVT = dyn_cast<StructType>(VT)) {
					// 获取操作数名称
					string ValueName = static_cast<string>(VI->getName());
					// 获取结构体名称
					string StructName = static_cast<string>(SVT->getName());
					// 插入VnameToTypenameMap中
					VnameToTypenameMap.insert(pair<string, string>(ValueName,StructName));
				}

			}
		}
	}
	// 这里返回false意味着初始化阶段不会对模块做任何的修改
	return false;
}
bool TypeInitializerPass::doFinalization(Module *M) {
	return false;
}

void TypeInitializerPass::BuildTypeStructMap(){
	// 根据前面构建的两个映射关系生成最终的全局类型映射
	// 详情参见9-11行的注释
	// build GlobalTypes based on TypeValueMap and VnameToTypenameMap	 
	for (auto const& P1 : TypeValueMap) {
		if (VnameToTypenameMap.find(P1.second) != VnameToTypenameMap.end()) {
			Ctx->GlobalTypes.insert(pair<Type*, string>(P1.first,VnameToTypenameMap[P1.second]));
		}

	}
	TypeToTNameMap = Ctx->GlobalTypes;
}

bool TypeInitializerPass::doModulePass(Module *M) {
	return false;
}
