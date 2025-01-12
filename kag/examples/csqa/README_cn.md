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

### Step 7：生成答案

在 [solver](./solver) 目录执行 [eval.py](./solver/eval.py) 生成答案。

```bash
cd solver && python eval.py && cd ..
```

生成的结果被保存至 ``./solver/data/csqa_kag_answers.json``.

### Step 8：（可选）获取其他系统生成的答案

按 LightRAG [Reproduce](https://github.com/HKUDS/LightRAG?tab=readme-ov-file#reproduce) 所述复现步骤生成问题的答案，将结果保存至 [./solver/data/csqa_lightrag_answers.json](./solver/data/csqa_lightrag_answers.json)。由于我们提交了一份 LightRAG 生成的答案，因此本步骤是可选的。

### Step 9：计算指标

更新 [summarization_metrics.py](./solver/summarization_metrics.py) 和 [factual_correctness.py](./solver/factual_correctness.py) 中的大模型配置并执行它们以计算指标。

```bash
python ./solver/summarization_metrics.py
python ./solver/factual_correctness.py
```

### Step 10：（可选）清理

若要删除 checkpoint，可执行以下命令。

```bash
rm -rf ./builder/ckpt
rm -rf ./solver/ckpt
```

若要删除 KAG 项目及关联的知识图谱，可执行以下类似命令，将 OpenSPG server 地址和 KAG 项目 id 换为实际的值。

```bash
curl http://127.0.0.1:8887/project/api/delete?projectId=1
```

