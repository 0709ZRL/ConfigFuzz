import json, os, re
import matplotlib.pyplot as plt
import numpy as np

# 统计所有配置项管辖代码行数量的分布情况

config_codeblock_path = 'config_codeblock.json'
config_tree_path = 'config_tree.json'

config_codeblock = None
config_tree = None

result = {}

def getLines(file, blockrange):
    print(blockrange)
    if blockrange == [0, 0]:
        res = os.popen("wc -l "+file).read().split()[0]
        res = int(res)
    else:
        res = blockrange[1] - blockrange[0] + 1
    return res
        

def getTotalLines(config):
    if config in result:
        # 如果已经被统计过了
        return

    res = 0
    codeblocks = config_codeblock.get(config)
    if not codeblocks:
        result[config] = 0
    else:
        for file, blockranges in codeblocks.items():
            for blockrange in blockranges:
                res += getLines(file, blockrange)
        result[config] = res
    
    offsets = config_tree.get(config)
    if offsets != None:
        for config in offsets:
            getTotalLines(config)

with open(config_codeblock_path, 'r') as f:
    config_codeblock = json.load(f)
with open(config_tree_path, 'r') as f:
    config_tree = json.load(f)

configs = config_codeblock.keys()
for config in configs:
    getTotalLines(config)

line_nums = []
for config, value in result.items():
    line_nums.append(value)

line_nums = sorted(line_nums)

with open("config_linenum.json", 'w+') as f:
    import json
    json.dump(result, f)

print("共{}个配置项。总和为{}行。".format(len(result), sum(line_nums)))
print("平均数为：{} 中位数为：{}".format(sum(line_nums)/len(line_nums), line_nums[len(line_nums)//2]))

plt.figure(figsize=(12, 6))
plt.title('Line Distribution Count')
plt.xlabel('Config')
plt.ylabel('Line Number')
plt.ylim(0, max(line_nums) + 100)
#plt.yscale('log')
plt.bar(range(len(line_nums)), line_nums, color='blue')
plt.savefig('line_distribution_count.png')