#-*-coding:utf-8 -*-

import os, sys, json

SINGLE_COMMENT = 1
COMMENT_START = 2
COMMENT_END = 3
BLANK = 4
COMMENT_KCONFIG = 5

def isComment(text):
    text = text.strip()
    if len(text) == 0:
        return BLANK
    if text.find('//') == 0:
        return SINGLE_COMMENT
    elif text.find('/*') >= 0:
        if text.find('/*') == 0 and text.find('*/') == len(text)-2:
            return SINGLE_COMMENT
        elif text.find('/*') > 0 and text.find('*/') > text.find('/*'):
            return 0
        elif text.find('/*') == 0:
            return COMMENT_START
    elif text.find('*/') == len(text)-2 and len(text) >= 2:
        return COMMENT_END
    elif text.find('#') == 0:
        return COMMENT_KCONFIG
    return 0
    
def getCodeSnippet(path):
    with open(path, 'r') as f:
        lines = f.readlines()
    output = []
    for i in range(len(lines)):
        output.append({'line':i+1,'text':lines[i]})
    return output

def getLines(snippet, format):
    num = 0
    long_comment = False
    for text in snippet:
        comment = isComment(text['text'])
        #print("line: {} comment: {}".format(text['line'], comment))
        if format == 'kconfig':
            if comment != COMMENT_KCONFIG:
                num += 1
        elif format == 'code':
            if comment == COMMENT_START:
                long_comment = True
            elif comment == COMMENT_END:
                long_comment = False
            elif comment == 0 or comment == 5:
                if not long_comment:
                    num += 1
    return num

def calculate(file_name, file_path):
    if file_name == 'Kbuild' or file_name == 'Kconfig' or file_name == 'Makefile':
        # return 0
        lines = getCodeSnippet(file_path)
        num = getLines(lines, 'kconfig')
        return num
    else:
        format = file_name.split('.')[-1]
        if format == 'c' or format == 'h' or format == 'S':
            lines = getCodeSnippet(file_path)
            num = getLines(lines, 'code')
            return num
        elif format == 'sh':
            lines = getCodeSnippet(file_path)
            num = getLines(lines, 'kconfig')
            return num
        return 0

if __name__ == '__main__':
    source_path = sys.argv[1]
    #source_path = 'linux-next/'+dirs
    
    #首先列出顶层的文件和目录列表，用以作为分类结果输出
    categories = os.listdir(source_path)
    
    others = 0 #如果顶层目录下就有文件，那么就把它归纳到others类输出。
    result_dict = {}

    for category in categories:
        category_path = os.path.join(source_path, category)
        if os.path.isfile(category_path):
            others += calculate(category, category_path)
        else:
            total = 0
            for path, dir_lst, file_lst in os.walk(category_path):
                for file_name in file_lst:
                    file_path = os.path.join(path, file_name)
                    print(file_path)
                    num = calculate(file_name, file_path)
                    total += num
            result_dict[category] = total
    result_dict['others'] = others
    print(result_dict)
    nums = [i for i in result_dict.values()]
    print(sum(nums))
    '''
    with open(dirs+'.json', 'w+') as f:
        json.dump(result_dict, f)
    '''