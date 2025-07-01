# KAG 示例：TwoWiki

[English](./README.md) |
[简体中文](./README_cn.md)

[2WikiMultiHopQA](https://arxiv.org/abs/2011.01060) 是一个用于对推理步骤进行全面评估的多跳问答数据集。[KAG](https://arxiv.org/abs/2409.13731) 和 [HippoRAG](https://arxiv.org/abs/2405.14831) 用它评估多跳问答的性能。

本例我们展示为 2WikiMultiHopQA 数据集构建知识图谱，然后用 KAG 为评估问题生成答案，并与标准答案对比计算 EM 和 F1 指标。

## 1. 前置条件

参考文档 [快速开始](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) 安装 KAG 及其依赖的 OpenSPG server，了解开发者模式 KAG 的使用流程。

## 2. 复现步骤

### Step 1：进入示例目录

```bash
cd kag/open_benchmark/2wiki
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

执行以下命令提交 schema [TwoWiki.schema](./schema/TwoWiki.schema)。

```bash
knext schema commit
```

### Step 5：构建知识图谱

在 [src](./src) 目录执行 [indexer.py](./src/indexer.py) 构建知识图谱。

```bash
cd src && python indexer.py && cd ..
```

### Step 6：执行 QA 任务

在 [src](./src) 目录执行 [eva.py](./src/eval.py) 生成答案并计算 EM 和 F1 指标。

```bash
cd src && python eval.py --qa_file ./data/qa_sub.json && cd ..
```

生成的答案被保存至 ``./src/2wiki_res_*.json``.

计算出的 EM 和 F1 指标被保存至 ``./src/2wiki_metrics_*.json``.

### Step 7：（可选）清理

若要删除 checkpoint，可执行以下命令。

```bash
rm -rf ./src/ckpt
```

### Step 8：（可选）尝试更大的数据集

从 Step 1 重新开始，修改 [indexer.py](./src/indexer.py) 和 [eval.py](./src/eval.py) 以尝试更大的数据集。

