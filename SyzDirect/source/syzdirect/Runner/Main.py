######## This is the main script

import Compilation
import Config
from SyscallAnalyze import SyscallAnalyze
import Fuzz

### Main

if __name__ == "__main__":
    actions=Config.Prepare()
    success = True

    if Config.Actions.PREPARE_SRC in actions:
        Config.logging.info("Start preparing kernel source for manual instrumentation")
        # 这里默认不对源码做checkout，因为网络可能会卡，耽误时间
        success = Compilation.PrepareSourceCode(True)
        Config.logging.info("Finish preparing kernel source for manual instrumentation")
        if not success:
            Config.logging.error("Some test cases failed, please check them manually.")
        exit(1)
        
    if Config.Actions.COMPILE_BITCODE in actions:
        Config.logging.info("Start compiling kernel bitcode for later analyzes")
        Compilation.CompileKernelToBitcodeNormal()
        Config.logging.info("Finish compiling kernel bitcode for later analyzes")

    # 生成内核函数的签名，构建内核函数和系统调用之间的映射关系
    # 生成的文件在workdir/interfaces/case_{caseIdx}/kernel_code2syscall.json
    # 具体的结构为：
    # “函数名”：{“函数里的代码块”：[“可以被什么系统调用触发”]}
    # 这里的函数名是经过处理的，去掉了__x64_sys_前缀
    if Config.Actions.ANALYZE_KERNEL in actions:
        Config.Check(Compilation.IsCompilationSuccessful,f"Not all cases have their bitcode not ready, please check or recompile the kernel")
        Config.logging.info("Start analyzing kernel syscall")
        SyscallAnalyze.AnalyzeKernelInterface()
        Config.logging.info("Finish analyzing kernel syscall")
    
    # 分析目标点位可以被哪些系统调用触发
    if Config.Actions.ANALYZE_TARGET_POINT in actions:
        Config.Check(SyscallAnalyze.IsSyscallInterfaceGenerated,"Not all cases have their interfaces successfully generated, please check or remove these case from caselist")
        Config.logging.info("Start analyzing target points")
        SyscallAnalyze.AnalyzeTargetPoints()
        Config.logging.info("Finish analyzing target points")
        
        
    if Config.Actions.INSTRUMENT_DISTANCE in actions:
        Config.logging.info("Start instrumenting kernel with distance")
        Config.Check(SyscallAnalyze.IsTargetPointAnalyzeSuccessful,"Not all cases have at least one point instrumented successfully, please check manually according to the message.")
        Compilation.CompileKernelToBitcodeWithDistance()
        Config.logging.info("Finish instrumenting kernel with distance")

    if Config.Actions.FUZZ in actions:    
        Config.logging.info("Start preparing for fuzzing")
        Fuzz.MultirunFuzzer()
        Config.logging.info("Finish preparing for fuzzing")
    

    