"""
# 使用undertaker和kbuildparser构建配置项->代码块的库。  
"""
import os, re, json, shutil, sys

file_codeblock = {}
config_codeblock = {}
paths = []

def parse_codeblock_range(res, src):
    """解析由undertaker解析出来的某一源文件的代码块。
    返回一个字典。字典格式：{文件路径：{基本块id: 基本块区间, ...}}"""
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

def parse_codeblock2configexp(res, src):
    """
    解析由undertaker解析出来的某一文件里各个代码块对应的配置项表达式。
    各个代码块的id与parse_codeblock_range返回的id对应。
    返回一个字典。字典格式：{文件路径：{基本块id: 配置项表达式, ...}}
    """
    total_dict = {}
    config_dict = {}
    for raw in res:
        if raw == '':
            continue
        # 可能存在一个bug，太长的字符串无法处理
        if len(raw) >= 512:
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
        print('exp: ', exp)
        # 将只有配置项的表达式插入到字典中
        config_dict[id] = exp
    total_dict[src] = config_dict
    return total_dict

def replace_block_id(exp, config_dict):
    """
    将配置项表达式中的代码块id换成对应的配置项表达式，得到一个只有配置项的表达式结果
    """
    matches = re.finditer(r'(?<![\dA-Z_])B\d+(?![\dA-Z_])', exp)
    for match in matches:
        start, end = match.start(), match.end()
        id = match.group()
        if config_dict.get(id):
            # 如果宏里没有配置项，那这个替换就没意义了，不做之
            if len(re.findall(r'CONFIG_[A-Z0-9_]+', exp)) == 0:
                continue
            exp = exp.replace(id, config_dict[id])
    return exp

def parse_config2codeblock(src, range_dict, file_config):
    """
    从file_config和range_dict中建立从配置项到代码块的反向映射，返回一个字典config_dict。  
    file_config来自于parse_codeblock2config的返回值。  
    range_dict来自于parse_codeblock_range的返回值(即file_codeblock)。  
    字典格式：{配置项:{路径:[代码区间1, 代码区间2, ...]}}
    """
    config_dict = {}
    ranges = range_dict[src]

    for blockid, exp in file_config[src].items():
        # 提取出每一个代码块的表达式里的配置项
        configs = re.findall(r'CONFIG_[A-Z0-9_]+', exp)
        for config in configs:
            # 这里注意：如果blockid是B00，代表整个文件都与某配置项相关，记作[0,0]
            if not config_dict.get(config):
                # 如果配置项对应的值为空，创建一个
                config_dict[config] = dict()
                if blockid == 'B00':
                    config_dict[config][src] = [[0,0]]
                else:
                    config_dict[config][src] = [ranges[blockid], ]
            else:
                # 如果配置项对应的值里从来没有当前文件的记录，创建一个
                if not config_dict[config].get(src):
                    if blockid == 'B00':
                        config_dict[config][src] = [[0,0]]
                    else:
                        config_dict[config][src] = [ranges[blockid], ]
                # 有该文件的记录，但是blockid是B00，优先保留粒度更细的版本（即配置项-代码块，而非配置项-整个文件）
                elif blockid == 'B00':
                    continue
                elif ranges[blockid] not in config_dict[config][src]:
                    # 如果有，那就直接加入到数组中即可（使用elif的原因是避免重复添加）
                    config_dict[config][src].append(ranges[blockid])
    return config_dict

def parse_codeblock(src, range_dict, config_cb):
    """
    根据prase_codeblock_range和parse_codeblock2config两个函数执行的结果来处理全局字典
    """
    # print('range_dict: ', range_dict)
    # print('config_cb: ', config_cb)
    if range_dict[src] == {} or config_cb[src] == {}:
        return
    # 处理config_codeblock
    config_dict = parse_config2codeblock(src, range_dict, config_cb)
    for config, value in config_dict.items():
        if not config_codeblock.get(config):
            config_codeblock[config] = value
        else:
            config_codeblock[config].update(value)

def parse_file_codeblock(src):
    """
    建立文件到代码块的映射。  
    返回格式：{路径：{id:区间，...}}
    """
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
            # 解析源码里有几个基本块区间
            res = os.popen("./undertaker.sh blockrange "+path).read().split()
            if res != None:
                range_dict = parse_codeblock_range(res, path)
            if range_dict[path] != None:
                file_codeblock.update(range_dict)
            print(path + " 解析完成。")

def parse_config_codeblock(src, file_codeblock_src):
    """
    建立配置项到代码块的映射。  
    流程为：首先抽取文件里各个代码块和配置项表达式，然后对表达式进行分析，最后将各个代码块id对应的区间和配置项建立映射。  
    返回结果：{配置项:{路径:[区间1，区间2，...]}}
    """
    if not os.path.exists(src):
        raise FileNotFoundError("内核源码目录不存在，请检查你的路径是否正确。由于不同配置环境不同，推荐使用绝对路径，而不要使用~, ../等符号。")
    
    # 需要读取文件到代码块的映射文件，以构建配置项->代码块id->代码块区间的联系。
    with open(file_codeblock_src, 'r') as f:
        file_codeblock = json.load(f)
    
    i = 0
    # 单线程版本
    for root, dirs, files in os.walk(src):
        for file in files:
            # 源码的路径
            path = os.path.join(root, file)
            # 源码的后缀名，不是代码文件不处理
            suffix = file.split('.')[-1]
            if suffix != 'c' and suffix != 'h' and suffix != 'S':
                continue

            # 解析源码里基本块和配置项表达式之间的关系
            res = os.popen("./undertaker.sh cpppc_decision "+path).read().split('\n')
            if res != None:
                configexp_dict = parse_codeblock2configexp(res, path)
            # 将配置项表达式拆成一个个配置项，以此建立代码块到配置项间的映射关系
            if len(configexp_dict[path]) > 0:
                config_dict = parse_config2codeblock(path, 
                                                     {path: file_codeblock.get(path)},
                                                     configexp_dict)
                # 更新全局字典
                config_codeblock_update(config_dict)
                i += 1
                # with open("cb_config_target/"+str(i)+".json", "w+") as f:
                #     json.dump(config_dict, f)
                #     i += 1
                # print(i)
                # if i >= 200:
                #     return

                # parse_codeblock(path, range_dict, configexp_dict)
                # codeblock_config这字典太大，导致内核容易OOM，现在只能退而求其次，先将结果统一存在文件里，再通过读取文件的方式，使用归并排序的思想融合成一个大的
                # with open("cb_config/"+str(i)+".json", "w+") as f:
                #     json.dump(configexp_dict, f)
                #     i += 1
            print(path + " 解析完成。")
            # paths.append(path)

    # # 将小codeblock_config融合成一个大的
    # print("正在进行codeblock_config融合...")
    # target_name = codeblock_config_merge(0, len(paths)-1, 'cb_config_target')
    # print(target_name)
    # # 尽力避免OOM
    # print("移动文件到工作目录...")
    # shutil.move('cb_config_target/0-36755.json', 'codeblock_exp.json')
        
    # # with open('file_codeblock.json', 'r') as f:
    # #     file_codeblock = json.load(f)
    # print("正在生成config_codeblock...")
    # with open('codeblock_exp.json', 'r') as f:
    #     codeblock_config_exp = json.load(f)
    # for dir, data in codeblock_config_exp.items():
    #     parse_codeblock(dir, 
    #                     {dir : file_codeblock.get(dir)},
    #                     {dir : data})
    #     print(dir + '已处理完成。')
    # del codeblock_config_exp

def parse_kbuildparser(src):
    """
    使用kbuildparser(其实就是从undertaker分出去的一个独立功能)获取配置项和整个源码文件之间的关系
    """
    paths = os.walk(src)
    configexp_dict = {}
    for path, dir_lst, file_lst in paths:
        for dir in dir_lst:
            # 获取每个目录的路径
            folder = os.path.join(path, dir)
            # 如果该目录下没有Makefile，那么kbuildparser解析不了，跳过
            if not os.path.exists(os.path.join(folder, 'Makefile')):
                continue
            # 开始使用kbuildparser解析
            print(folder)
            res = os.popen("kbuildparser/kbuildparser {}".format(folder))
            res = res.read().split('\n')
            for result in res:
                # 格式：目录 <- 配置项
                result_split = result.split('<-')
                if len(result_split) < 2:
                    continue
                file, config_exp = result_split[0].strip(), result_split[1].strip()
                file = os.path.abspath(file)
                configexp_dict[file] = {'B00' : config_exp}
                config_dict = parse_config2codeblock(file,
                                                     {file: file_codeblock.get(file)},
                                                     configexp_dict)
                config_codeblock_update(config_dict)

def config_codeblock_update(config_dict):
    """
    更新config_codeblock这个全局大字典
    """
    for config, data in config_dict.items():
        if not config_codeblock.get(config):
            config_codeblock[config] = data
        else:
            for path, ranges in data.items():
                if not config_codeblock[config].get(path):
                    config_codeblock[config][path] = ranges
                else:
                    for range in ranges:
                        if range not in config_codeblock[config][path]:
                            config_codeblock[config][path].append(range)

def codeblock_config_merge(start, stop, target_dir):
    """
    使用归并排序的方式将所有的小文件合成一个大的codeblock_config.json  
    ## 注：此功能目前已废弃
    """
    # print(start, ' ', stop)
    data = None
    if start >= stop:
        with open(paths[stop], 'r') as f:
            data = json.load(f)
    else:
        mid = (start + stop) // 2
        upper = codeblock_config_merge(start, mid, target_dir)
        lower = codeblock_config_merge(mid + 1, stop, target_dir)
        # 做归并
        upper_data, lower_data = None, None
        with open(target_dir + '/' + upper, 'r') as f:
            upper_data = json.load(f)
        with open(target_dir + '/' + lower, 'r') as f:
            lower_data = json.load(f)
        data = upper_data
        data.update(lower_data)
        os.remove(target_dir + '/' + upper)
        os.remove(target_dir + '/' + lower)
    with open(target_dir + '/' + str(start) + '-' + str(stop) + '.json', 'w+') as f:
        json.dump(data, f)
    return str(start) + '-' + str(stop) + '.json'

if __name__ == '__main__':
    # 你是想抽取文件->代码块的关系，还是配置项->代码块的关系呢？
    # 注意，构建配置项->代码块前要先构建文件->代码块哦！
    option = sys.argv[1]
    # 待解析的内核源码的路径
    kernel_src = sys.argv[2]
    # 文件->代码块映射保存地址
    file_codeblock_src = sys.argv[3]
    if option == 'file_codeblock':
        # 构建文件->代码块
        parse_file_codeblock(kernel_src)
        # 保存
        with open(file_codeblock_src, "w+") as f:
            json.dump(file_codeblock, f)
    elif option == 'config_codeblock':
        # 构建配置项->代码块
        # 再提醒一次，构建配置项->代码块前要先构建文件->代码块哦！
        config_codeblock_src = sys.argv[4]
        parse_config_codeblock(kernel_src, file_codeblock_src)
        # 用kbuildparser构建配置项->整个文件的关系，一并加入到全局大字典中
        parse_kbuildparser(kernel_src)
        # 保存
        with open(config_codeblock_src, "w+") as f:
            json.dump(config_codeblock, f)