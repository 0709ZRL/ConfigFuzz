import json

file_codeblock, codeblock_config = None, None

# 给出一个配置项名，找到所有它管辖的代码块。
# 返回格式：{路径:[代码区间1, 代码区间2, ...]}
# 如果代码区间是0,0，证明范围是整个文件。
def find_by_config(config):
    return codeblock_config.get(config)

if __name__ == "__main__":
    with open("config_codeblock.json", "r") as f:
        codeblock_config = json.load(f)
    res = find_by_config('CONFIG_HOTPLUG_CPU')
    print(res)