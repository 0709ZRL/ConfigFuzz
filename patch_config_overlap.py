'''
1、匹配每一个patch内有多少行代码被配置项包裹 以及占比是多少
'''
import re, json, sys, os

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

def create(patch_json_path, target_path, linux_path):
    commit_re = r'Commit: [a-z0-9]+'
    file_re = r'File: [A-Za-z0-9/_.]+'
    lines_re = r'Lines: [0-9]+-[0-9]+'

    patches = []

    commit_hash = None
    file = None
    files = {}
    
    for line in open(patch_json_path, 'r'):
        print("commithash: {} file: {}".format(commit_hash, file))
        res = re.findall(commit_re, line)
        if res:
            if commit_hash and files:
                print("Commit: {} Files: {}".format(commit_hash, files))
                patch = Patch(commit_hash, files)
                patches.append(patch)
                commit_hash, files = None, None
            commit_hash = res[0].split(': ')[1]
            file = None
            files = {}
            continue
        res = re.findall(file_re, line)
        if res:
            file = res[0].split(': ')[1]
            # patch_json里面都是相对路径，需要把linux_path加上构成绝对路径
            file = os.path.join(linux_path, file)
            file = os.path.abspath(file)
            continue
        res = re.findall(lines_re, line)
        if res:
            line_ranges = res[0].split(': ')[1]
            lines = line_ranges.split('-')
            if file not in files:
                files[file] = [[int(lines[0]), int(lines[1])]]
            else:
                files[file].append([int(lines[0]), int(lines[1])])
            continue
    
    with open(target_path, 'w+') as f:
        res = {}
        for patch in patches:
            res[patch.commit] = {'files': patch.files, 'total_lines': patch.total_lines}
        json.dump(res, f)

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

def calculate(patches_path, config_codeblock_path):
    patches = {}
    config_codeblocks = {}
    new_patches = []

    with open(patches_path, 'r') as f:
        patches = json.load(f)
    with open(config_codeblock_path, 'r') as f:
        config_codeblocks = json.load(f)
    
    covered_codeblocks = {}
    for config, file_dict in config_codeblocks.items():
        for file, ranges in file_dict.items():
            for span in ranges:
                if file not in covered_codeblocks:
                    covered_codeblocks[file] = [span, ]
                else:
                    if span != [0, 0]:
                        covered_codeblocks[file].append(span)
                    else:
                        covered_codeblocks[file] = [[0, 0]]
                        break
    del config_codeblocks

    for commit, values in patches.items():
        patch = Patch(commit, values['files'])
        covered_lines = 0
        for file, ranges in patch.files.items():
            # print(file, " ", ranges)
            if file not in covered_codeblocks:
                continue
            else:
                for span in ranges:
                    if [0, 0] in covered_codeblocks[file]:
                        patch.config_covered_lines += span[1] - span[0] + 1
                    else:
                        for config_span in covered_codeblocks[file]:
                            patch.config_covered_lines += get_overlap(span, config_span)
        patch.config_covered_ratio = patch.config_covered_lines / patch.total_lines
        new_patches.append(patch)
        #print("commit: {} total_lines: {} config_covered_lines: {} config_covered_ratio: {}".format(patch.commit, patch.total_lines, patch.config_covered_lines, patch.config_covered_ratio))
    
    with open(patches_path, 'w+') as f:
        res = {}
        for patch in new_patches:
            res[patch.commit] = {'files': patch.files, 'total_lines': patch.total_lines, 'config_covered_lines': patch.config_covered_lines, 'config_covered_ratio': patch.config_covered_ratio}
        json.dump(res, f)

if __name__ == '__main__':
    option = sys.argv[1]
    
    if option == 'create':
        patch_json_path = sys.argv[2] # 生成的patch_json在哪？
        target_path = sys.argv[3] # 目标文件路径
        linux_path = sys.argv[4] # linux源码路径
        if not os.path.exists(target_path):
            # 如果目标文件不存在，则创建
            create(patch_json_path, target_path, linux_path)
    elif option == 'config':
        patches_path = sys.argv[2] # 上面用create生成的文件
        config_codeblock_path = sys.argv[3]
        calculate(patches_path, config_codeblock_path)
    elif option == 'show':
        patches_path = sys.argv[2]
        the_number_of_patches_covered_by_configs = 0
        all_covered_number = 0
        total_lines = 0
        config_covered_lines = 0
        with open(patches_path, 'r') as f:
            patches = json.load(f)
        for commit, patch in patches.items():
            if patch['config_covered_ratio'] > 0:
                the_number_of_patches_covered_by_configs += 1
                config_covered_lines += patch['config_covered_lines']
                if patch['config_covered_ratio'] == 1:
                    all_covered_number += 1
                print("commit: {} total_lines: {} config_covered_lines: {} config_covered_ratio: {}".format(commit, patch['total_lines'], patch['config_covered_lines'], patch['config_covered_ratio']))
            total_lines += patch['total_lines']
        print("the ratio of patches covered by configs: {}/{}".format(the_number_of_patches_covered_by_configs, len(patches)))
        print("the ratio of patches totally covered by configs: {}/{}".format(all_covered_number, the_number_of_patches_covered_by_configs))
        print("total ratio: {}".format(config_covered_lines / total_lines))