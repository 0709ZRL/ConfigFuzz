#include "ConfigParser.h"
#include <iostream>

using namespace std;

unordered_map<string, Config*> *configs;

template<typename T>
unordered_map<string, T>* readJsonFile(const string& filename, unordered_map<string, T>* (*parser)(const Json::Value&, unordered_map<string, T>* originalMap), unordered_map<string, T>* originalMap) {
    Json::Value root;
    // Json::Reader json_reader; 这玩意不是Json::parseFromStream的参数之一？
    Json::CharReaderBuilder json_builder;
    string errors;
    
    ifstream file(filename);
    if (!file.is_open())
        throw runtime_error("Could not open file: " + filename);

    if (!Json::parseFromStream(json_builder, file, &root, &errors))
        throw runtime_error("Failed to parse JSON: " + errors);

    return parser(root, originalMap);
}

unordered_map<string, Config*>* configTreeParser(const Json::Value& Root, unordered_map<string, Config*>* originalMap) {
    unordered_map<string, Config*>* result;

    if (originalMap == nullptr)
        result = new unordered_map<string, Config*>();
    else
        result = originalMap;

    auto get_or_create = [&](const string& name) {
        if (result->count(name) == 0)
            (*result)[name] = new Config{name, {}, {}, {}, {}};
        return (*result)[name];
    };

    for (const auto& key : Root.getMemberNames()) {
        string key_str(key);
        Config* parent = get_or_create(key_str);
        (*result)[key_str] = parent;

        for (const auto& child : Root[key_str]) {
            const string child_name = child.asString();
            parent->children.push_back(get_or_create(child_name));
        }
    }

    return result;
}

unordered_map<string, Config*>* configCodeBlockParser(const Json::Value& Root, unordered_map<string, Config*>* originalMap) {
    unordered_map<string, Config*>* result;
    int begin, end;

    if (originalMap == nullptr)
        result = new unordered_map<string, Config*>();
    else
        result = originalMap;
        
        auto get_or_create = [&](const string& name) {
            if (result->count(name) == 0)
                (*result)[name] = new Config{name, {}, {}, {}, {}};
            return (*result)[name];
        };

    for (const auto& key : Root.getMemberNames()) {
        string key_str(key);
        Config* config = get_or_create(key_str);
        const Json::Value& fileranges = Root[key_str];
        for (const auto& file_path : fileranges.getMemberNames()) {
            const Json::Value& ranges = fileranges[file_path];
            for (const auto& range : ranges) {
                begin = range[0].asInt();
                end = range[1].asInt();
                // if (key_str == "CONFIG_STM32_DFSDM_ADC")
                //     cout << "Processing range for " << key_str << ": [" << begin << ", " << end << "] in " << file_path << endl;
                FileRange file_range = {file_path, static_cast<unsigned int>(begin), static_cast<unsigned int>(end)};
                config->ranges.push_back(file_range);
            }
        }
        (*result)[key_str] = config;
    }

    return result;
}

const vector<FileRange> &getCoveredConfigBlocks(Config &config) {
    if (!configs->count(config.name))
        throw runtime_error("Config not found: " + config.name);
    return config.ranges;
}

const vector<Config*> &getParentConfigs(Config &config) {
    if (!configs->count(config.name))
        throw runtime_error("Config not found: " + config.name);
    return config.fathers;
}

const vector<Config*> &getChildConfigs(Config &config) {
    if (!configs->count(config.name))
        throw runtime_error("Config not found: " + config.name);
    return config.children;
}

const vector<Config*> &getSiblingConfigs(Config &config) {
    if (!configs->count(config.name))
        throw runtime_error("Config not found: " + config.name);
    return config.siblings;
}

int main(){
    configs = readJsonFile<Config*>("/home/zzzrrll/ConfigFuzz/data-6.15.0/config_tree.json",  configTreeParser, nullptr);
    // 不知道为什么，一个配置项会被处理两遍？
    configs = readJsonFile<Config*>("/home/zzzrrll/ConfigFuzz/data-6.15.0/config_codeblock.json",  configCodeBlockParser, configs);
    cout<<"configs.size() = "<< configs->size() <<endl;
    for (const auto& pair : *configs) {
        cout << "Config name: " << pair.second->name << endl;
        cout << "Ranges: ";
        for (const auto& range : pair.second->ranges) {
            cout << "{" << range.src << ", " << range.startLine << ", " << range.endLine << "} ";
        }
        cout << "Children: ";
        for (const auto& child : pair.second->children) {
            cout << child->name << " ";
        }
        cout << "Fathers: ";
        for (const auto& father : pair.second->fathers) {
            cout << father->name << " ";
        }
        cout << "Siblings: ";
        for (const auto& sibling : pair.second->siblings) {
            cout << sibling->name << " ";
        }
        cout << endl;
    }
    delete configs;
    return 0;
}