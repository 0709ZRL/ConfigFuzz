import Config
import os
import json
from . import InterfaceGenerate,TargetPointAnalyze

def AnalyzeKernelInterface():
    # function_modeling
    Config.logging.info("#### Analyzing kernel interface")
    
    # generate syzkaller signature
    Config.logging.info("Generating signature for syzkaller")

    # 先用syzkaller的syz-features根据当前的使用环境生成内核签名，标注了内核各个系统调用的基本情况和可支持的各个子系统情况等
    syzkaller_signature_cmd=f"{Config.SyzFeaturePath} > {Config.SyzkallerSignaturePath}"
    print(syzkaller_signature_cmd)
    Config.ExecuteCMD(syzkaller_signature_cmd)
    assert os.path.exists(Config.SyzkallerSignaturePath) and os.stat(Config.SyzkallerSignaturePath).st_size!=0, "Fail to syzkaller signature!!!"
    Config.logging.info(f"Generating syzkaller signature successfully!")
    
    # 对于每一个要测试的点位
    for datapoint in Config.datapoints:
        caseIdx=datapoint['idx']
        # workdir/interfaces/case_{caseIdx}目录
        caseInterfaceWorkingDir=Config.PrepareDir(Config.getInterfaceDirByCase(caseIdx))
        # 拿到先前编译好的bitcode文件（.llbc格式）
        caseBitcodeDir=Config.getBitcodeDirByCase(caseIdx)
        # 内核签名文件的存放位置(workdir/interfaces/case_{caseIdx}/kernel_signature_full)
        caseKernelSignatureFile=Config.getKernelSignatureByCase(caseIdx)
        # 使用interface_generator分析每一个内核函数
        if not os.path.exists(caseKernelSignatureFile):
            generating_cmd=f"cd {caseInterfaceWorkingDir} && {Config.FunctionModelBinary} --verbose-level=4 {caseBitcodeDir} 2>&1 | tee log"
            Config.logging.debug(f"[case {caseIdx}] Starting generating kernel signature")
            Config.ExecuteBigCMD(generating_cmd)
            
            if os.path.exists(caseKernelSignatureFile):
                Config.logging.info(f"[case {caseIdx}] Generating kernel signature successfully!")
            else:
                Config.logging.error(f"[case {caseIdx}] Fail to generate kernel signature !!!")
                continue
            
        print(Config.SyzkallerSignaturePath, caseKernelSignatureFile)
        kernelCode2syscall = InterfaceGenerate.MatchSig(Config.SyzkallerSignaturePath, caseKernelSignatureFile)

        caseFinalInterfaceFile=Config.getFinalInterfaceParingResultByCase(caseIdx)
        # 存到interfaces/case_{caseIdx}/kernel_code2syscall.json里
        # 具体的结构为：
        # “函数名”：{“函数里的代码块”：[“可以被什么系统调用触发”]}
        with open(caseFinalInterfaceFile, mode="w") as f:
            json.dump(kernelCode2syscall, f, indent="\t")
            
        if os.path.exists(caseFinalInterfaceFile):
            Config.logging.info(f"[case {caseIdx}] Final interface result generated successfully!")
        else:
            Config.logging.error(f"[case {caseIdx}] Fail to generate final interface result!!!")
       
                        
    # return all fail cases, [] if all succeed
def IsSyscallInterfaceGenerated():
    return [
        datapoint['idx'] for datapoint in Config.datapoints if not os.path.exists(Config.getFinalInterfaceParingResultByCase(datapoint['idx']))
    ]
        
        
def AnalyzeTargetPoints():
    # kernel analysis
    Config.logging.info("#### Analyzing syscall entry and calculating distance per block")
    
    Config.logging.info("Generating syscall pair map")
    syscall_pair_map_cmd=f"cd {Config.WorkdirPrefix} && {Config.SyzTRMapPath}"
    Config.ExecuteCMD(syscall_pair_map_cmd)
    assert os.path.exists(Config.SyzTRMapPath), "Failed to generate syscall pair map. Please check"
    Config.logging.info(f"Generating syscall pair map successfully!")
    
    for datapoint in Config.datapoints:
        caseIdx=datapoint['idx']
        caseFinalInterfaceFile=Config.getFinalInterfaceParingResultByCase(caseIdx)
        caseBitcodeDir=Config.getBitcodeDirByCase(caseIdx)
        caseKernelAnalysisResDir=Config.PrepareDir(Config.getTargetPointAnalysisResultDirByCase(caseIdx))
        
        Config.logging.info(f"[case {caseIdx}] Analyzing syscall entry and calculating distance")
        # target_analyzer是这么用的！看好了！
        analyze_cmd=f"cd {caseKernelAnalysisResDir} && {Config.TargetPointAnalysisBinary} --verbose-level=4 -kernel-interface-file={caseFinalInterfaceFile} -multi-pos-points={Config.getMultiPointsSpecificFile(caseIdx)} {caseBitcodeDir} 2>&1 | tee log"
        Config.ExecuteBigCMD(analyze_cmd)
        if os.path.exists(Config.getTargetPointAnalysisDuplicateReport(caseIdx)):
            Config.logging.error(f"[case {caseIdx}] has multi-points!!! need manual check!!!")
            Config.logging.error(f"Duplicate points are reported in {Config.getTargetPointAnalysisDuplicateReport(caseIdx)}")
            Config.logging.error("Please specify getMultiPointsSpecificFile(lambda function) in Config.py according to your multi-points file structure")
            Config.logging.error("Default set to workdir/multi-pts/case_{caseIdx}.txt")
            Config.logging.error("The format of multi-points file. Example: ")
            Config.logging.error("0 some_function_you_want")
            Config.logging.error("1 some_other_function_you_want")
            Config.logging.error("... and_other_function_you_want")
            continue
        if not os.path.exists(Config.getTargetPointAnalysisMidResult(caseIdx)):
            Config.logging.error(f"[case {caseIdx}] fail to analyze target point")
            continue
        Config.logging.info(f"[case {caseIdx}] Finish analyzing syscall entry and calculate distance")
        
        Config.logging.info(f"[case {caseIdx}] Postprocessing the result, preparing for fuzzing")
        TargetPointAnalyze.PrepareForFuzzing(caseIdx,datapoint['recommend syscall'])
        
        
def IsTargetPointAnalyzeSuccessful():
    return [
        datapoint['idx'] for datapoint in Config.datapoints if not os.path.exists(Config.getFuzzInpDirPathByCase(datapoint['idx'])) or os.stat(Config.getFuzzInpDirPathByCase(datapoint['idx'])).st_size==0
    ]