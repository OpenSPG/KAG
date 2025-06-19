# KAG 示例：Peaple Realation Query & Answer

[English](./README.md) |
[简体中文](./README_cn.md)

[PRQA](Peaple Realation Query & Answer) 是一个由浙江大学知识图谱团队提出的针对图谱评测的数据集。[KAG](https://arxiv.org/abs/2409.13731)。

本例我们展示为 AffairQA数据集构建知识图谱，然后用 KAG 为评估问题生成答案，并与标准答案对比计算 EM 和 F1 指标。

## 1. 前置条件

参考文档 [快速开始](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) 安装 KAG 及其依赖的 OpenSPG server，了解开发者模式 KAG 的使用流程。

## 2. 复现步骤

### Step 1：进入示例目录

```bash
cd kag/open_benchmark/prqa
```

### Step 2：配置模型

更新 [kag_config.yaml](./kag_config.yaml) 中的生成模型配置 ``openie_llm`` 和 ``chat_llm`` 和表示模型配置 ``vectorize_model``

您需要设置正确的 ``api_key``。如果使用的模型供应商和模型名与默认值不同，您还需要更新 ``base_url`` 和 ``model``。

更新 [kag_config.yaml](./kag_config.yaml) 中的 kag-solver configuration 关于 ``prqa_executor`` 中的 neo4j 配置

您需要配置neo4j的用户名和密码
### Step 3：初始化项目

先对项目进行初始化。

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### Step 4：提交 schema

执行以下命令提交 schema  [PRQA.schema](./schema/PRQA.schema)。

```bash
knext schema commit
```

### Step 5：构建知识图谱

在 [builder](./builder) 目录执行 [indexer.py](./builder/indexer.py) 构建知识图谱。

```bash
cd builder && python indexer.py && cd ..
```

### Step 6：执行 QA 任务

首先在 [evalForPR.py](solver/evalForPR.py) 代码的main函数中填入neo4j的用户名和密码

在 [solver](./solver) 目录执行 [evalForPR.py](solver/evalForPR.py) 生成答案

```bash
cd solver && python evalForPR.py && cd ..
```

生成的答案被保存至 ``./solver/data/result.txt``.

执行答案判断及F1和EM计算过程：
```bash
python ./evaluator.py
```

### Step 7：（可选）清理

若要删除 checkpoint，可执行以下命令。

```bash
rm -rf ./builder/ckpt
rm -rf ./solver/ckpt
```

