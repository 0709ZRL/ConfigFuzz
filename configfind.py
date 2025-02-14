import json

file_codeblock, codeblock_config = None, None
config_tree = None

def find_by_config(config):
    """
    给出一个配置项名，找到所有它管辖的代码块。
    返回格式：{路径:[代码区间1, 代码区间2, ...]}
    如果代码区间是0,0，证明范围是整个文件。
    """
    return codeblock_config.get(config)

def get_father_config(config):
    """
    获取配置项config的父配置项。
    例：CONFIG_A depends on !CONFIG_B || CONFIG_C
    则CONFIG_A的父配置项同时为CONFIG_B和CONFIG_C。
    """
    return config_tree.get(config)

def get_son_config(config):
    """
    获取配置项config的子配置项。
    例：CONFIG_A depends on !CONFIG_B || CONFIG_C
    则CONFIG_B和CONFIG_C的子配置项都为CONFIG_A。
    """
    configs = []
    for son_config, deps in config_tree.items():
        if config in deps:
            configs.append(son_config)
    return configs

def get_sibling_config(config):
    """
    获取配置项config的兄弟配置项。
    例：CONFIG_A depends on !CONFIG_B || CONFIG_C，
    同时CONFIG_D depends on CONFIG_B，
    则CONFIG_A和CONFIG_D互为兄弟配置项。
    FIXME::这里暂时没有考虑配置项表达式值的问题。在上面的例子中，严格讲A和D不应该是兄弟，因为他们互斥。
    """
    configs = []
    if config_tree.get(config) == None:
        return None
    for key, deps in config_tree.items():
        for dep_config in deps:
            if dep_config in config_tree.get(config):
                configs.append(key)
                break
    return configs

if __name__ == "__main__":
    # with open("config_codeblock.json", "r") as f:
    #     codeblock_config = json.load(f)
    # res = find_by_config('CONFIG_HOTPLUG_CPU')
    # print(res)

    queue = []
    with open("config_tree.json", 'r') as f:
        config_tree = json.load(f)
    config = 'CONFIG_SMP'
    print(config, "的父配置项是：", get_father_config(config))
    print(config, "的子配置项是：", get_son_config(config))
    print(config, "的兄弟配置项是：", get_sibling_config(config))