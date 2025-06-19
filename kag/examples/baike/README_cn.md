# KAG 示例：百科问答（BaiKe）

[English](./README.md) |
[简体中文](./README_cn.md)

## 1. 前置条件

参考文档 [快速开始](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) 安装 KAG 及其依赖的 OpenSPG server，了解开发者模式 KAG 的使用流程。

## 2. 复现步骤

### Step 1：进入示例目录

```bash
cd kag/examples/baike
```

### Step 2：配置模型

更新 [kag_config.yaml](./kag_config.yaml) 中的生成模型配置 ``openie_llm`` 和 ``chat_llm`` 和表示模型配置 ``vectorize_model``。

您需要设置正确的 ``api_key``。如果使用的模型供应商和模型名与默认值不同，您还需要更新 ``base_url`` 和 ``model``。

### Step 3：初始化项目

先对项目进行初始化。

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### Step 4：提交 schema

执行以下命令提交 schema [BaiKe.schema](./schema/BaiKe.schema)。

```bash
knext schema commit
```

### Step 5：构建知识图谱

在 [builder](./builder) 目录执行 [indexer.py](./builder/indexer.py) 构建知识图谱。

```bash
cd builder && python indexer.py && cd ..
```

### Step 6：执行 QA 任务

在 [solver](./solver) 目录执行 [eval.py](./solver/eval.py) 问示例问题并查看答案和 trace log。

```bash
cd solver && python eval.py && cd ..
```

我们在 KAG 中实现了 MCP server，可以将 KAG 构建的知识库通过 MCP server 的形式暴露出来，供支持 MCP 协议的 Agent 集成。参考 [KAG MCP Server 示例：百科问答（BaiKe）](./mcp_server_cn.md)。

### Step 7：（可选）清理

若要删除 checkpoint，可执行以下命令。

```bash
rm -rf ./builder/ckpt
```

