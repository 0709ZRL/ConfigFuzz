import argparse
from enum import Enum
import logging
import os
import pandas as pd
import subprocess
import json
import yaml

### global definition
class Actions(Enum):
    PREPARE_SRC = "prepare_for_manual_instrument"
    COMPILE_BITCODE = "prepare_kernel_bitcode"
    ANALYZE_KERNEL = "analyze_kernel_syscall"
    ANALYZE_TARGET_POINT = "extract_syscall_entry"
    INSTRUMENT_DISTANCE = "instrument_kernel_with_distance"
    FUZZ = "fuzz"

### Logging
logging.basicConfig(
    level=logging.INFO,
    # filename="syzdirect.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s: %(message)s"
)

#### helper funtions
def Check(func,fail_str):
    fail_cases=func()
    assert len(fail_cases)==0, f"{fail_str}\n Fail cases: {','.join(fail_cases)}"
    
def LoadDatapoints():
    # 读取.xlsx文件
    res = pd.read_excel(DatasetFile)
    header = res.columns
    # 全局变量
    global datapoints
    datapoints=[dict(zip(header,i)) for i in res.values]
    logging.info(f"{len(datapoints)} data points loaded from {DatasetFile}.")
    for datapoint in datapoints:
        # 为了测试这个bug，需要特殊的配置文件位置(可以没有)，如果没有就用默认的bigconfig
        if pd.isna(datapoint['config path']):
            logging.debug(f"{datapoint['idx']} Using default bigconfig path")
            print(datapoint)
            datapoint['config path'] = BigConfigPath
        # 为了测试这个bug，需要特殊的系统调用(可以没有)，如果没有就是空
        if pd.isna(datapoint['recommend syscall']):
            datapoint['recommend syscall']=[]
        else:
            datapoint['recommend syscall'] = datapoint['recommend syscall'].split(',')
        assert os.path.exists(datapoint['config path'])
    logging.debug(res)
    
def ExecuteCMD(cmd):
    logging.debug(f"Executing: {cmd}")
    p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    p.wait()
    return str(p.stdout.read(),encoding="utf-8"),str(p.stderr.read(),encoding="utf-8")

def ExecuteBigCMD(cmd):
    logging.debug(f"Executing big: {cmd}")
    os.system(cmd)
    
def PrepareDir(*dirname):
    if len(dirname)>1:
        dirname=os.path.join(*dirname)
    else:
        dirname=dirname[0]
    os.makedirs(dirname,exist_ok=True)
    return dirname

def PrepareTempFile(*filename):
    if len(filename)>1:
        filename=os.path.join(*filename)
    else:
        filename=filename[0]
    # if os.path.exists(filename):
    #     os.remove(filename)
    return filename

def LoadJson(fn):
    with open(fn, "r") as fp:
        return json.load(fp)
    
def PreparePathVariables(config):
    global KcovPatchPath,LLVMRootDir,LLVMBuildDir,ClangPath,BigConfigPath,TemplateConfigPath,FuzzerDir,FuzzerBinDir,SyzManagerPath,SyzTRMapPath,SyzFeaturePath
    
    KcovPatchPath = config['KcovPatchPath']
    LLVMRootDir = config['LLVMRootDir']
    LLVMBuildDir = os.path.join(LLVMRootDir,"build")
    ClangPath = os.path.join(LLVMBuildDir,"bin/clang")
    BigConfigPath = config['BigConfigPath']
    TemplateConfigPath = config['TemplateConfigPath']
    FuzzerDir = config['FuzzerDir']
    FuzzerBinDir = os.path.join(FuzzerDir,"bin")
    SyzManagerPath = os.path.join(FuzzerBinDir,"syz-manager")
    SyzTRMapPath = os.path.join(FuzzerBinDir,"direct")
    SyzFeaturePath = os.path.join(FuzzerBinDir,"syz-features")

    ###################### working directory ######################
    global WorkdirPrefix
    WorkdirPrefix = os.path.abspath(PrepareDir(WorkdirPrefix))

    ### source code
    global SrcDirRoot,getSrcDirByCase
    SrcDirRoot=PrepareDir(WorkdirPrefix,"srcs")
    getSrcDirByCase=lambda caseIdx: os.path.join(SrcDirRoot,f"case_{caseIdx}")

    ### bitcode 
    global BitcodeDirRoot,getBitcodeDirByCase
    BitcodeDirRoot=PrepareDir(WorkdirPrefix,"bcs")
    getBitcodeDirByCase=lambda caseIdx: os.path.join(BitcodeDirRoot,f"case_{caseIdx}")

    ### function model result
    global FunctionModelDirRoot,FunctionModelBinary,InterfaceDirRoot,getInterfaceDirByCase, getKernelSignatureByCase,getFinalInterfaceParingResultByCase
    FunctionModelDirRoot = config['FunctionModelDirRoot']
    FunctionModelBinary = os.path.join(FunctionModelDirRoot,"build/lib/interface_generator")
    InterfaceDirRoot = PrepareDir(WorkdirPrefix,"interfaces")
    getInterfaceDirByCase = lambda caseIdx: os.path.join(InterfaceDirRoot,f"case_{caseIdx}")
    getKernelSignatureByCase = lambda caseIdx: os.path.join(getInterfaceDirByCase(caseIdx),"kernel_signature_full")
    getFinalInterfaceParingResultByCase = lambda caseIdx: os.path.join(getInterfaceDirByCase(caseIdx),"kernelCode2syscall.json")

    ### analyzing target point and calculate distance
    global TargetPointAnalysisDirRoot,TargetPointAnalysisBinary,getTargetPointAnalysisResultDirByCase,getTargetPointAnalysisMidResult,getTargetPointAnalysisDuplicateReport,getMultiPointsSpecificFile,getDistanceResultDir,getTargetFunctionInfoFile

    TargetPointAnalysisDirRoot = config['TargetPointAnalysisDirRoot']
    TargetPointAnalysisBinary = os.path.join(TargetPointAnalysisDirRoot,"build/lib/target_analyzer")
    TargetPointAnalysisResultDirRoot = PrepareDir(WorkdirPrefix,"tpa")
    getTargetPointAnalysisResultDirByCase = lambda caseIdx: os.path.join(TargetPointAnalysisResultDirRoot,f"case_{caseIdx}")
    getTargetPointAnalysisMidResult = lambda caseIdx: os.path.join(getTargetPointAnalysisResultDirByCase(caseIdx),"CompactOutput.json")
    getTargetPointAnalysisDuplicateReport = lambda caseIdx: os.path.join(getTargetPointAnalysisResultDirByCase(caseIdx),"duplicate_points.txt")
    getTargetFunctionInfoFile = lambda caseIdx: os.path.join(getTargetPointAnalysisResultDirByCase(caseIdx),"target_functions_info.txt")
    getDistanceResultDir = lambda caseIdx, xIdx: os.path.join(getTargetPointAnalysisResultDirByCase(caseIdx),f"distance_xidx{xIdx}")
    getMultiPointsSpecificFile = lambda caseIdx: os.path.join(WorkdirPrefix, "multi-pts", f"case_{caseIdx}.txt")

    ### post-processing
    global getConstOutDirPathByCase,getConstOutFilePathByCaseAndXidx, getFuzzInpDirPathByCase,getFuzzInpDirPathByCaseAndXidx
    ConstOutWorkingDirRoot = PrepareDir(WorkdirPrefix,"consts")
    getConstOutDirPathByCase = lambda caseIdx: os.path.join(ConstOutWorkingDirRoot, f"case_{caseIdx}")
    getConstOutFilePathByCaseAndXidx = lambda caseIdx, xIdx: os.path.join(getConstOutDirPathByCase(caseIdx), f"const_xidx{xIdx}.json")

    FuzzInpWorkingDirRoot = PrepareDir(WorkdirPrefix,"fuzzinps")
    getFuzzInpDirPathByCase = lambda caseIdx: os.path.join(FuzzInpWorkingDirRoot, f"case_{caseIdx}")
    getFuzzInpDirPathByCaseAndXidx = lambda caseIdx, xIdx: os.path.join(getFuzzInpDirPathByCase(caseIdx), f"xidx{xIdx}.json")

    ### temp file 
    # generated during execution -- may not exists
    global TRMapPath,SyzkallerSignaturePath,EmitScriptPath
    EmitScriptPath=PrepareTempFile(WorkdirPrefix,"emit-llvm.sh")
    SyzkallerSignaturePath=PrepareTempFile(WorkdirPrefix,"syzkaller_signature.txt")
    TRMapPath=PrepareTempFile(WorkdirPrefix,"target2relate2.json")

    ### fuzz
    global getFuzzResultDirByCase, getFuzzResultDirByCaseAndXidx,getCustomizedSyzByCaseAndXidx
    FuzzingResultDirRoot = PrepareDir(WorkdirPrefix,"fuzzres")
    getFuzzResultDirByCase = lambda caseIdx: os.path.join(FuzzingResultDirRoot, f"case_{caseIdx}")
    getFuzzResultDirByCaseAndXidx = lambda caseIdx, xIdx: os.path.join(getFuzzResultDirByCase(caseIdx), f"xidx{xIdx}")
    getCustomizedSyzByCaseAndXidx = lambda caseIdx, xIdx: os.path.join(getFuzzResultDirByCaseAndXidx(caseIdx, xIdx), "syzkaller")

    ### instrument with distance
    global getInstrumentedKernelImageByCaseAndXidx,getInstrumentedKernelDirByCase
    InstrumentedKernelDirRoot = PrepareDir(WorkdirPrefix,"kwithdist")
    getInstrumentedKernelDirByCase = lambda caseIdx: os.path.join(InstrumentedKernelDirRoot, f"case_{caseIdx}")
    getInstrumentedKernelImageByCaseAndXidx = lambda caseIdx, xIdx: os.path.join(getInstrumentedKernelDirByCase(caseIdx), f"bzImage_{xIdx}")

    ############### SET BY USER
    global CleanImageTemplatePath,KeyPath
    CleanImageTemplatePath = config['CleanImageTemplatePath']
    KeyPath = config['KeyPath']
    assert os.path.exists(CleanImageTemplatePath), "Please offer clean image path"
    assert os.path.exists(KeyPath), "Please offer key path"

def ParseTargetFunctionsInfoFile(caseIdx):
    tfmap={}
    with open(getTargetFunctionInfoFile(caseIdx)) as f:
        for row in f.readlines():
            row=row.split(" ")
            xidx=row[0]
            target_function=row[1]
            target_function_path=row[2]
            tfmap[xidx]=(target_function,target_function_path)
    return tfmap

#### arg parser
def PrepareArgParser():
    global WorkdirPrefix,DatasetFile,LinuxSrcTemplate,CPUNum,FuzzRounds,FuzzUptime
    logging.debug("Start preparing arg parser")

    parser=argparse.ArgumentParser(description='This is the runner script for Syzdirect.')
    
    # 你要干什么
    parser.add_argument('actions',type=Actions, nargs='+', metavar="/".join([a.value for a in Actions]),help='actions to be chose from')
    # yaml配置文件位置
    parser.add_argument('-config',type=str, default="config.yaml",help='config file for syzdirect, default set to config.yaml',required=True)
    
    arg=parser.parse_args()
    
    file = open(arg.config)
    config = yaml.load(file)
    file.close()

    WorkdirPrefix=config['WorkdirPrefix']
    DatasetFile=config['Dataset']

    # 检查bug数据集是否存在且后缀格式合法
    print("DatasetFile: ", os.path.exists(DatasetFile))
    assert os.path.exists(DatasetFile) and os.path.splitext(DatasetFile)[1] == ".xlsx", "dataset file (default set to ${WorkdirPrefix}/dataset.xlsx) not exists or it's not ended with .xlsx"

    # 从工作目录中准备其下各个工具的路径变量
    PreparePathVariables(config)

    CPUNum = config['CPUNum']
    FuzzRounds = config['FuzzRounds']
    FuzzUptime = config['FuzzUptime']
    
    # 检查linux源码仓库是否存在，如果不存在设成None
    LinuxSrcTemplate = config['LinuxSrcTemplate']
    if not os.path.exists(LinuxSrcTemplate):
        LinuxSrcTemplate = None

    return arg.actions

def PrepareBinary():
    ### 编译LLVM
    if not os.path.exists(ClangPath):
        logging.info("Automatically build customized llvm")
        makecmd=f'cd {LLVMRootDir} && cmake -S llvm -B build -DLLVM_ENABLE_PROJECTS=clang -DCMAKE_BUILD_TYPE=Release && cmake --build build -j {CPUNum}' 
        # print(ExecuteCMD(makecmd)[0])
        ExecuteBigCMD(makecmd)
    assert os.path.exists(ClangPath), "Fails to build customized llvm(clang)"
        
    ### function_model
    if not os.path.exists(FunctionModelBinary):
        logging.info("Building tool for function modeling")
        build_function_model_cmd=f'cd {FunctionModelDirRoot} && make clean && make LLVM_BUILD={LLVMBuildDir}'
        # print(ExecuteCMD(build_function_model_cmd)[0])
        ExecuteBigCMD(build_function_model_cmd)
        assert os.path.exists(FunctionModelBinary), "Fails to build function modeling tool"
    
    ### kernel_analysis
    if not os.path.exists(TargetPointAnalysisBinary):
        logging.info("Building tool for entry extract and distance calculation")
        build_kernel_analysis_cmd=f"cd {TargetPointAnalysisDirRoot} && make clean && make LLVM_BUILD={LLVMBuildDir}"
        ExecuteBigCMD(build_kernel_analysis_cmd)
        assert os.path.exists(TargetPointAnalysisBinary), "Fails to build tool for entry extract and distance calculation"
    
    ### 编译Syzkaller模糊测试器
    if not (os.path.exists(SyzManagerPath) and os.path.exists(SyzFeaturePath)):
        logging.info("Building fuzzer")
        build_fuzzer_cmd=f"cd {FuzzerDir} && make"
        ExecuteBigCMD(build_fuzzer_cmd)
        assert os.path.exists(FuzzerBinDir), "Fails to build fuzzer"
        logging.info("Manual check is expected for all the binaries in the bin/, e.p. syz-fuzzer, syz-manager...")


def Prepare():
    # 解析输入参数
    actions=PrepareArgParser()
    # 加载数据点
    LoadDatapoints()
    # 准备二进制内核镜像
    PrepareBinary()
    return actions