# 在哪里获取的系统调用间依赖关系，以及在哪里使用？
## 获取依赖关系
在syzdirect_fuzzer/prog/direct.go代码中定义。该代码会生成direct程序，执行该程序会生成relate2context2.json文件，结构如下：
```
{
    "系统调用名$次级描述符": {
        "Module": 该调用所属的模块，由syzkaller自己识别。
        "FullVersion": 所有用到该系统调用输出的调用，目测大多数都为Null。
        "SimpleVersion": 在更严格的规则下，用到该系统调用输出的系统调用列表。
        "TrimVersion": 精简版的SimpleVersion，实际只用到这个。
    }
}
```
Syzkaller所用的具体规则在direct.go的isCompatibleResourceImpl函数中，目测是显式依赖，和我们暂时无关。
## 使用依赖关系
在TargetPointAnalyze.py的PrepareForFuzzing函数中，这个文件会被读取，会被再次修剪处理存到Config.getFuzzInpDirPathByCaseAndXidx(caseIdx,xidx)所指向的文件中。  
因此我们可以在这里做文章。
