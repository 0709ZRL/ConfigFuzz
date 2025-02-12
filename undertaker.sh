#!/bin/bash

# 定义递归读取文件并处理的函数
function blockrange {
    filename=$(basename "$1")
    filedir=$(dirname "$1")
    file=$1

    # 以一定时间限制执行命令
    if timeout 30s undertaker -j blockrange "$file"; then
        return 0
    else
        return -1
    fi
}

function cpppc {
    filename=$(basename "$1")
    filedir=$(dirname "$1")
    file=$1

    # 以一定时间限制执行命令
    if timeout 30s undertaker -j cpppc_decision "$file"; then
        return 0
    else
        return -1
    fi
}

# 检查是否提供了命令
if [[ -z "$1" ]]; then
    echo "Usage: $0 <option> <directory>"
    exit 1
fi

# 检查是否提供了目录参数
if [[ -z "$2" ]]; then
    echo "Usage: $0 <function> <directory>"
    exit 1
fi

if [ "$1" = "blockrange" ]; then
    blockrange $2
fi

if [ "$1" = "cpppc_decision" ]; then
    cpppc $2
fi