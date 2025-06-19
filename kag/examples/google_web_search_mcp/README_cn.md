# KAG 示例:  Google Web Search MCP

[English](./README.md) |
[简体中文](./README_cn.md)

这里是一个 Google Web Search MCP，将用户输入的搜索问题作为输入，返回相关的网页。在此处只是展示 MCP 的执行效果，如果需要链接到 KAG 上进行检索，请访问 OpenSPG 创建对应的知识库和应用，将 MCP 链接到 KAG 中并使用。

## 1. 前置条件

参考文档 [快速开始](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) 安装 KAG 及其依赖的 OpenSPG server，了解开发者模式 KAG 的使用流程。

## 2. 复现步骤

### Step 1：进入示例目录

```bash
cd kag/examples/google_web_search_mcp
```

### Step 2：配置模型

更新 [kag_config.yaml](./kag_config.yaml) 中的生成模型配置 ``chat_llm``。

您需要设置正确的 ``api_key``。如果使用的模型供应商和模型名与默认值不同，您还需要更新 ``base_url`` 和 ``model``。

### Step 3：执行 QA 任务

在目录中执行 [google_web_search_client.py](./google_web_search_client.py)。

```bash
python google_web_search_client.py
```

问题示例：

1. 天空为什么是蓝色的？
2. 什么是丁达尔效应？

启动后请您输入想要询问的问题，我们会通过 Google 检索到相关的网页，然后将结果返还给您。

