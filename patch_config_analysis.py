'''
对patch进行基于配置项的依赖分析。
'''
import json, os, sys

class Patch():
    def __init__(self, commit, files):
        self.commit = commit
        self.files = files
        self.total_lines = 0
        self.config_covered_lines = 0
        self.config_covered_ratio = 0
        for file, ranges in files.items():
            for line_range in ranges:
                self.total_lines += line_range[1] - line_range[0] + 1

patches, config_codeblock, config_tree, covered_codeblocks = None, None, None, {}

def get_overlap(span, config_span):
    if span[0] <= config_span[0] and span[1] >= config_span[1]:
        return config_span[1] - config_span[0] + 1
    elif span[0] >= config_span[0] and span[1] <= config_span[1]:
        return span[1] - span[0] + 1
    elif span[0] <= config_span[0] and span[1] <= config_span[1]:
        return span[1] - config_span[0] + 1
    elif span[0] >= config_span[0] and span[1] >= config_span[1]:
        return config_span[1] - span[0] + 1
    else:
        return 0

def getContents(file, line_range, f):
    """
    获取文件的指定行范围的内容
    """
    if not os.path.exists(file) or os.path.isdir(file):
        return f
    with open(file, 'r') as p:
        lines = p.readlines()
        f.write(''.join(lines[line_range[0]-1:line_range[1]]))
    return f
    
def getOverlapConfig(file, line_range):
    if file not in covered_codeblocks:
        return None
    for config, ranges in covered_codeblocks[file].items():
        if [0, 0] in ranges:
            return config
        else:
            for config_span in ranges:
                overlaps = get_overlap(line_range, config_span)
                if overlaps > 0:
                    return config

def getConfigContent(config, f):
    file_dict = config_codeblock.get(config)
    for file, ranges in file_dict.items():
        f.write('文件：{}\n'.format(file))
        p = open(file, 'r')
        lines = p.readlines()
        if [0, 0] in ranges:
            # f.write(''.join(lines))
            continue
        else:
            f.write(''.join(lines[line_range[0]-1:line_range[1]]))
        p.close()
    return f

if __name__ == '__main__':
    patch_dir = sys.argv[1]
    config_codeblock_dir = sys.argv[2]
    config_tree_dir = sys.argv[3]
    output_dir = sys.argv[4]

    with open(patch_dir, 'r') as f:
        patches = json.load(f)
        tmp = []
        for commit, patch_data in patches.items():
            patch = Patch(commit, patch_data['files'])
            patch.config_covered_lines = patch_data['config_covered_lines']
            patch.config_covered_ratio = patch_data['config_covered_ratio']
            patch.total_lines = patch_data['total_lines']
            tmp.append(patch)
        patches = tmp
    
    with open(config_codeblock_dir, 'r') as f:
        config_codeblock = json.load(f)
    for config, file_dict in config_codeblock.items():
        for file, ranges in file_dict.items():
            for span in ranges:
                if file not in covered_codeblocks:
                    covered_codeblocks[file] = {}
                    covered_codeblocks[file][config] = [span,]
                else:
                    if config not in covered_codeblocks[file]:
                        if span != [0, 0]:
                            covered_codeblocks[file][config] = [span, ]
                        else:
                            covered_codeblocks[file][config] = [[0, 0]]
                            break
                    else:
                        if span != [0, 0]:
                            covered_codeblocks[file][config].append(span)
                        else:
                            covered_codeblocks[file][config] = [[0, 0]]
                            break
    
    with open(config_tree_dir, 'r') as f:
        config_tree = json.load(f)

    f = open(output_dir, 'w+')
    
    for patch in patches:
        f.write("提交哈希：{}\n".format(patch.commit))
        f.write("总行数：{} 被配置项覆盖的行数：{} 覆盖率：{}\n".format(patch.total_lines, patch.config_covered_lines, patch.config_covered_ratio))

        if patch.config_covered_lines == 0:
            continue
        
        configs = []
        for file, ranges in patch.files.items():
            f.write("文件：{}\n".format(file))
            for line_range in ranges:
                f.write("行范围：{}-{}\n".format(line_range[0], line_range[1]))
                f = getContents(file, line_range, f)
                f.write("\n")
                config = getOverlapConfig(file, line_range)
                if config and config not in configs:
                    configs.append(config)
        for config in configs:
            f.write("配置项：{}\n".format(config))
            f.write("配置项内容：\n")
            f = getConfigContent(config, f)
            f.write("\n")
    f.close()