# KAG 示例：CSQA

[English](./README.md) |
[简体中文](./README_cn.md)

[UltraDomain](https://huggingface.co/datasets/TommyChien/UltraDomain/tree/main) ``cs.jsonl`` 数据集包含 10 个计算机科学领域的文档，和关于这些文档的 100 个问题及答案。

本例我们展示为如何为这些文档构建知识图谱，用 KAG 为这些问题生成答案，并与其他 RAG 系统生成的答案进行比较。

## 1. 前置条件

参考文档 [快速开始](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) 安装 KAG 及其依赖的 OpenSPG server，了解开发者模式 KAG 的使用流程。

## 2. 复现步骤

### Step 1：进入示例目录

```bash
cd kag/examples/csqa
```

### Step 2：（可选）准备数据

下载 [UltraDomain](https://huggingface.co/datasets/TommyChien/UltraDomain/tree/main) ``cs.jsonl`` 并执行 [generate_data.py](./generate_data.py) 在 [./builder/data](./builder/data) 和 [./solver/data](./solver/data) 中生成数据文件。由于我们提交了生成的文件，因此本步骤是可选的。

```bash
python generate_data.py
```

### Step 3：配置模型

更新 [kag_config.yaml](./kag_config.yaml) 中的生成模型配置 ``openie_llm`` 和 ``chat_llm`` 和表示模型配置 ``vectorize_model``。

您需要设置正确的 ``api_key``。如果使用的模型供应商和模型名与默认值不同，您还需要更新 ``base_url`` 和 ``model``。

配置 ``splitter`` 和 ``num_threads_per_chain`` 可能也需要更新以与其他系统匹配。

### Step 4：初始化项目

先对项目进行初始化。

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### Step 5：提交 schema

执行以下命令提交 schema [CsQa.schema](./schema/CsQa.schema)。

```bash
knext schema commit
```

### Step 6：构建知识图谱

在 [builder](./builder) 目录执行 [indexer.py](./builder/indexer.py) 构建知识图谱。

```bash
cd builder && python indexer.py && cd ..
```

### Step 7：执行 QA 任务

在 [solver](./solver) 目录执行 [eval.py](./solver/eval.py) 生成答案。

```bash
cd solver && python eval.py && cd ..
```

### Step 8：（可选）清理

若要删除 checkpoint，可执行以下命令。

```bash
rm -rf ./builder/ckpt
rm -rf ./solver/csqa_ckpt
```

