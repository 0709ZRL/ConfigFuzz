"""
# 使用kconfiglib构建配置项树的库。
"""
import sys, os, json

from kconfiglib import Kconfig, Symbol, Choice
from kconfiglib import KconfigError
from kconfiglib import AND, OR, NOT, EQUAL, UNEQUAL, LESS, LESS_EQUAL, GREATER, GREATER_EQUAL

# 关系运算符字典，构建配置项表达式可能会有用
REALTION_MAP = {
    AND: '&&',
    OR: '||',
    NOT: '!',
    EQUAL: '==',
    UNEQUAL: '!=',
    LESS: '<',
    LESS_EQUAL: '<=',
    GREATER: '>',
    GREATER_EQUAL: '>='
}
# 黑名单，该名单目录下的Kconfig不解析，因为需要复杂的环境变量
blacklist = ["Kconfig"]
# 存储配置项树的全局大字典
config_tree = {}

def get_dep_exp(direct_dep):
    """
    将某个配置项的依赖关系direct_dep(Symbol.item.direct_dep类型)递归转换成包含配置项的集合。  
    返回值：一个集合set，里面包括direct_dep里的所有配置项，即某个配置项依赖的配置项。
    """
    # print(direct_dep)
    if isinstance(direct_dep, Symbol):
        # 该配置项只依赖于一个配置项，简单处理即可
        return set(['CONFIG_'+direct_dep.name])
    elif not isinstance(direct_dep, tuple):
        # 该配置项的依赖关系里包含无法处理的内容，不处理之。直接返回。
        return None
    # 依赖关系元组一般为如下格式：(运算符，运算数1，运算数2（如果有）……)
    # 可以参考编译原理中的二元/三元运算符的表达形式。
    deps = set()
    # 运算符
    operand = REALTION_MAP.get(direct_dep[0])
    if operand == None:
        raise NotImplementedError("配置项表达式中出现未见过的运算符。")
    # 依次处理各个运算数（因为运算数可能也是一个元组）
    for i in range(1, len(direct_dep)):
        operator = get_dep_exp(direct_dep[i])
        if operator != None:
            deps.update(operator)
    # 处理完后返回
    return deps

def Update(config, deps):
    """
    更新配置项树。  
    """
    if not config_tree.get(config):
        config_tree[config] = deps
    else:
        if deps == {}:
            return
        config_tree[config].update(deps)

def get_items(node):
    """
    递归获取一个Kconfig节点（一般为一个配置项）的依赖关系。  
    并用之更新配置项树全局大字典。
    """
    while node:
        if isinstance(node.item, Symbol):
            # 该节点是一个配置项
            deps = {}
            if node.item.direct_dep == node.kconfig.y:
                # 没有依赖关系
                print("Symbol: ", 'CONFIG_'+node.item.name)
            elif isinstance(node.item.direct_dep, Symbol):
                # 该节点的依赖关系就只是一个配置项，简单处理即可
                deps = set(['CONFIG_'+node.item.direct_dep.name])
                print("Symbol: ", 'CONFIG_'+node.item.name, "Symbol Dependency: ", deps)
            elif isinstance(node.item.direct_dep, tuple):
                # 该节点的依赖关系是个元组，处理一下
                #print(node.item.direct_dep)
                deps = get_dep_exp(node.item.direct_dep)
                print("Symbol: ", 'CONFIG_'+node.item.name, "Tuple Dependency: ", deps)
            # else:
            #     print("Symbol: ", node.item.name, " Dependency type: ", type(node.item.direct_dep))

            # 将结果更新到全局大字典里
            Update('CONFIG_'+node.item.name, deps)
        # 如果该节点下还有节点则处理之
        if node.list:
            get_items(node.list)
        node = node.next

# kconf = Kconfig(sys.argv[1]) 
# get_items(kconf.top_node)
if __name__ == '__main__':
    kconfigs = []
    # 待解析的内核源码地址
    src = sys.argv[1]
    # 存储配置项树全局大字典的文件路径
    config_tree_src = sys.argv[2]

    # 设置一下环境变量
    # 防止kconfiglib解析时出现未知的bug
    # FIXME::解析时出错就不管，那这个还有用吗？设了能让出错频率降低？
    os.environ["KERNELVERSION"] = "6.15.0"
    os.environ['srctree'] = src
    os.environ['CC'] = 'gcc'
    os.environ['LD'] = 'ld'

    # 将内核源码目录下所有的Kconfig都抽出来
    for root, dirs, files in os.walk(src):
        for file in files:
            if 'Kconfig' in file:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, src)
                #if relative_path in blacklist:
                    #continue 
                kconfigs.append(os.path.join(root, file))
    
    # 挨个解析
    for kconfig in kconfigs:
        print('Kconfig file: ', kconfig)
        # 成功就记录，不成功就不管
        # （实际发现，这么做后能成功解析的配置项个数跟配置项->代码块映射记录里的配置项个数差不多，或许是这个方法可行的有力论证？除非你构建配置项->代码块映射的方法也很弱，那我就没话说了）
        try:
            kconf = Kconfig(kconfig) 
            get_items(kconf.top_node)
        except KconfigError:
            continue
    
    # 集合格式无法被json库存储，将其转换为列表形式
    for key, value in config_tree.items():
        config_tree[key] = list(value)
    # 存储
    with open(config_tree_src, 'w+') as f:
        json.dump(config_tree, f)