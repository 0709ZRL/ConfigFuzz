import json, os, re

# 统计x86架构下所有可配置的配置项管辖的代码行有多少

config_codeblock_path = 'config_codeblock.json'
config_tree_path = 'config_tree.json'
configdirectory_path = '/home/zzzrrll/linux/arch/x86/configs/x86_64_defconfig'

config_codeblock = None
config_tree = None
total = 0

counted_lines = {}
searched_configs = []

def getLines(file, blockrange):
    #print(blockrange)
    if blockrange == [0, 0]:
        res = os.popen("wc -l "+file).read().split()[0]
        res = int(res)
    else:
        res = blockrange[1] - blockrange[0] + 1
    return res
        

def getTotalLines(config):
    res = 0

    if config in searched_configs:
        # 如果已经被统计过了
        return 0
    
    searched_configs.append(config)
    codeblocks = config_codeblock.get(config)
    if not codeblocks:
        return 0
    
    for file, blockranges in codeblocks.items():
        for blockrange in blockranges:
            if not counted_lines.get(file):
                res += getLines(file, blockrange)
                counted_lines[file] = [blockrange, ]
            else:
                for i in range(len(counted_lines[file])):
                    foundrange = counted_lines[file][i]
                    if foundrange == [0, 0]:
                        # 整个文件都被统计过
                        break
                    elif foundrange[0] <= blockrange[0] <= blockrange[1] <= foundrange[1]:
                        # 被大的包裹
                        break
                    elif blockrange[0] < foundrange[0] <= foundrange[1] < blockrange[1]:
                        # 包裹一个被找过的小的
                        res -= foundrange[1] - foundrange[0] + 1
                        res += getLines(file, blockrange)
                        counted_lines[i] = blockrange
                        break
                    else:
                        # 没被找到过
                        res += getLines(file, blockrange)
                        counted_lines[file].append(blockrange)
                        break
    
    offsets = config_tree.get(config)
    if offsets != None:
        for config in offsets:
            res += getTotalLines(config)

    return res

with open(config_codeblock_path, 'r') as f:
    config_codeblock = json.load(f)
with open(config_tree_path, 'r') as f:
    config_tree = json.load(f)

target_architecture_configs = []
for line in open(configdirectory_path, 'r'):
    configs = re.findall(r'CONFIG_[A-Z0-9_]+', line)
    if len(configs) == 1:
        if re.findall(r'is not set', line):
            continue
        target_architecture_configs.append(configs[0])

for config in target_architecture_configs:
    total += getTotalLines(config)

print("一共找了{}个配置项。".format(len(searched_configs)))
print("总共{}行。".format(total))

# x86 6132121
# 5.4 18640244