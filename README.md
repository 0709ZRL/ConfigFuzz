# ConfigFuzz
本目录存储了ConfigFuzz项目所需的所有文件，请您参照以下说明编译与使用此项目。
## 工作流程
本项目首先使用基于undertaker和kbuildparser的工具进行内核配置项提取与分析，将内容以字典的形式保存起来。  
然后使用LLVM插件基于配置项信息与内核的CFG（以llvm bitcode, .llbc格式构建）实现目标点位的依赖捕捉。  
最后使用syzkaller进行模糊测试。  
## 编译与安装
### undertaker
按如下步骤安装：  
1、获取undertaker
```
git clone https://github.com/ultract/original-undertaker-tailor.git
```
2、安装必要的库，编译并安装undertaker
```
cd original-undertaker
sudo apt-get install libboost1.55-dev libboost-filesystem1.55-dev libboost-regex1.55-dev libboost-thread1.55-dev libboost-wave1.55-dev libpuma-dev libpstreams-dev check python-unittest2 clang sparse pylint
make
make install
```
3、最后输入undertaker正确执行即成功。
### syzkaller
1、将sys/sys.go注释成如下格式：
```
// Use of this source code is governed by Apache 2 LICENSE that can be found in the LICENSE file.

package sys

import (
        // Import all targets, so that users only need to import sys.
        // _ "github.com/google/syzkaller/sys/akaros/gen"
        // _ "github.com/google/syzkaller/sys/darwin/gen"
        // _ "github.com/google/syzkaller/sys/freebsd/gen"
        // _ "github.com/google/syzkaller/sys/fuchsia/gen"
        _ "github.com/google/syzkaller/sys/linux/gen"
        // _ "github.com/google/syzkaller/sys/netbsd/gen"
        // _ "github.com/google/syzkaller/sys/openbsd/gen"
        // _ "github.com/google/syzkaller/sys/test/gen"
        // _ "github.com/google/syzkaller/sys/trusty/gen"
        // _ "github.com/google/syzkaller/sys/windows/gen"
)
```
2、安装1.23.4版本的go于当前目录下，并设置环境变量：
```
wget https://dl.google.com/go/go1.23.4.linux-amd64.tar.gz
tar -xf go1.23.4.linux-amd64.tar.gz
export GOROOT=`pwd`/go
export PATH=$GOROOT/bin:$PATH
```
3、正式安装syzkaller：
```
cd syzdirect_fuzzer && make
```