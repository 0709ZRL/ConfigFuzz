import os, re, json

file_codeblock = {}
config_codeblock = {}
codeblock_config = {}

# 解析由undertaker解析出来的某一源文件的代码块。
# 返回一个字典。字典格式：{文件路径：{基本块id: 基本块区间, ...}}
def parse_codeblock_range(res, src):
    range_dict = {}
    src_dict = {}
    for raw in res:
        if raw == '':
            continue
        raw_split = raw.split(':')
        # 基本块id，是字符串
        block_id = raw_split[1]
        # 基本块开始的位置，是整数
        block_begin = int(raw_split[2])
        # 基本块结束的位置，是整数
        block_end = int(raw_split[3])
        # 如果成功解析出了基本块开始与结束的位置，则将该基本块的信息加入到字典中
        if not block_begin and not block_end:
            continue
        src_dict[block_id] = [block_begin, block_end]
    # 将该文件对应的字典加入到大字典中，并返回该字典。
    range_dict[src] = src_dict
    return range_dict

# 解析由undertaker解析出来的某一文件里各个代码块对应的配置项。
# 各个代码块的id与parse_codeblock_range返回的id对应。
# 返回一个字典。字典格式：{文件路径：{基本块id: 配置项表达式, ...}}
def parse_codeblock2config(res, src):
    total_dict = {}
    config_dict = {}
    for raw in res:
        if raw == '':
            continue
        # 找到字符串中代码块对应的配置项表达式的位置
        matches = re.search('\( B[0-9]+ <-> ', raw)
        if not matches:
            continue
        exp_begin = matches.end()
        exp = raw[exp_begin : -2]
        # 找到字符串中代码块id的位置
        matches2 = re.search('B[0-9]+', raw)
        if not matches2:
            continue
        id = matches2.group()
        # 将配置项表达式中的代码块id换成对应的配置项表达式，得到一个只有配置项的表达式结果
        exp = replace_block_id(exp, config_dict)
        # 将只有配置项的表达式插入到字典中
        config_dict[id] = exp
    total_dict[src] = config_dict
    return total_dict

# 将配置项表达式中的代码块id换成对应的配置项表达式，得到一个只有配置项的表达式结果
def replace_block_id(exp, config_dict):
    matches = re.finditer(r'(?<![\dA-Z_])B\d+(?![\dA-Z_])', exp)
    for match in matches:
        start, end = match.start(), match.end()
        id = match.group()
        if config_dict.get(id):
            exp = exp.replace(id, config_dict[id])
    return exp

# 从file_config和range_dict中建立从配置项到代码块的反向映射，返回一个字典config_dict。
# file_config来自于parse_codeblock2config的返回值。
# range_dict来自于parse_codeblock_range的返回值。
# 字典格式：{配置项:{路径:[代码区间1, 代码区间2, ...]}}
def parse_config2codeblock(src, file_config, range_dict):
    config_dict = {}
    ranges = range_dict[src]
    for blockid, exp in file_config.items():
        # 提取出每一个代码块的表达式里的配置项
        configs = re.findall(r'CONFIG_[A-Z0-9_]+', exp)
        for config in configs:
            if not config_dict.get(config):
                # 如果配置项对应的值为空，创建一个
                config_dict[config] = dict()
                config_dict[config][src] = [ranges[blockid], ]
            else:
                # 如果配置项对应的值里从来没有当前文件的记录，创建一个
                if not config_dict[config].get(src):
                    config_dict[config][src] = [ranges[blockid], ]
                elif ranges[blockid] not in config_dict[config][src]:
                    # 如果有，那就直接加入到数组中即可（使用elif的原因是避免重复添加）
                    config_dict[config][src].append(ranges[blockid])
    return config_dict

# 根据prase_codeblock_range和parse_codeblock2config两个函数执行的结果来处理全局字典
def parse_codeblock(src, range_dict, config_cb):
    # 处理file_codeblock
    file_codeblock[src] = range_dict[src]
    # 处理config_codeblock
    config_dict = parse_config2codeblock(src, config_cb, range_dict)
    for config, value in config_dict.items():
        if not config_codeblock.get(config):
            config_codeblock[config] = value
        else:
            config_codeblock[config].update(value)

def parse(src):
    if not os.path.exists(src):
        raise FileNotFoundError("内核源码目录不存在，请检查你的路径是否正确。由于不同配置环境不同，推荐使用绝对路径，而不要使用~, ../等符号。")
    
    # 单线程版本
    for root, dirs, files in os.walk(src):
        for file in files:
            # 源码的路径
            path = os.path.join(root, file)
            # 源码的后缀名
            suffix = file.split('.')[-1]
            if suffix != 'c' and suffix != 'h' and suffix != 'S':
                continue
            # 首先解析源码里有几个基本块区间
            res = os.popen("./undertaker.sh blockrange "+path).read().split()
            if res != None:
                range_dict = parse_codeblock_range(res, path)
            # 接着解析源码里基本块和配置项之间的关系
            res = os.popen("./undertaker.sh cpppc "+path).read().split()
            if res != None:
                config_dict = parse_codeblock2config(res, path)
            # 将上面两步的结果存到全局字典中
            if range_dict[path] != None:
                file_codeblock.update(range_dict)
            if config_dict[path] != None:
                codeblock_config.update(config_dict)
            print(path + " 解析完成。")

if __name__ == '__main__':
    parse('/home/zzzrrll/linux-5.4')
    with open("file_codeblock.json", "w+") as f:
        json.dump(file_codeblock, f)
    with open("codeblock_config.json", "w+") as f:
        json.dump(file_codeblock, f)