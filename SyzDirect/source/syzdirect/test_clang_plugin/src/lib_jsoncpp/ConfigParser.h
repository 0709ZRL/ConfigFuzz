#include <string>
#include <vector>
#include <utility>
#include <fstream>
#include <stdexcept>
#include <unordered_map>
#include <json/json.h>

using namespace std;

// 定义必要的类型
// 1、一个配置项管辖的代码范围结构体
typedef struct {
    string src; // 文件路径
    // 注：如果以下两个值为0，表示该文件的所有行都在范围内
    unsigned int startLine; // 起始行
    unsigned int endLine; // 结束行
} FileRange;

// 2、配置项
typedef struct Config{
    string name; // 名称
    vector<FileRange> ranges; // 管辖的代码范围
    // 一个配置项的关联配置项指自己和它的父，子，兄弟节点
    vector<struct Config*> fathers; // 父节点
    vector<struct Config*> children; // 子节点
    vector<struct Config*> siblings; // 兄弟节点
} Config;

// 通用函数声明
// 读取一个json文件，将结果返回到一个vector列表中，至于如何解析json文件，交给函数指针parser所指的函数，它会将json里的每一个对象解析成一个特定的结构，vector里存储的就是这种结构。
// filename: json文件路径
// originalMap: 用于存储配置项数据的vector，如果你是第一次调用readJsonFile，则可以设成NULL；反之请设成上一次调用返回的vector的指针。
template<typename T>
unordered_map<string, T>* readJsonFile(const string& filename, unordered_map<string, T>* (*parser)(const Json::Value&, unordered_map<string, T>* originalMap), unordered_map<string, T>* originalMap);

// 解析config_tree.json的函数
unordered_map<string, Config*>* configTreeParser(const Json::Value& Root, unordered_map<string, Config*>* originalMap);
// 解析config_codeblock.json的函数
unordered_map<string, Config*>* configCodeBlockParser(const Json::Value& Root, unordered_map<string, Config*>* originalMap);

// 获取一个配置项管辖的所有代码范围(FileRange格式，非基本块)
const vector<FileRange> &getCoveredConfigBlocks(Config &config);
// 获取一个配置项的父节点
const vector<Config*> &getParentConfigs(Config &config);
// 获取一个配置项的子节点
const vector<Config*> &getChildConfigs(Config &config);
// 获取一个配置项的所有兄弟节点
const vector<Config*> &getSiblingConfigs(Config &config);