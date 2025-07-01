# KAG AffairQA

[English](./README.md) |
[简体中文](./README_cn.md)

AffairQA是一个由浙江大学知识图谱团队提出的针对图谱评测的数据集。在现代社会中，政务服务的数字化和智能化正逐步推进，以提高政府工作效率和公众满意度。知识图谱（Knowledge Graph, KG）作为一种结构化信息管理方式，通过语义关联和语境理解，为政务服务提供了全面的事实和数据支持。在涉及复杂政策、法规和程序时，快速而准确的信息检索能力显得尤为重要。本数据集专注于政务问答任务，旨在从一个大型知识图谱中检索出政务事实，来回答相关问题。我们设定输入为一个特定的政务问题，输出则是从知识图谱中提取到的用于回答问题的事实。收到

本例我们展示为 AffairQA数据集构建知识图谱，然后用[KAG](https://arxiv.org/abs/2409.13731) 为评估问题生成答案，并与标准答案对比计算 EM 和 F1 指标。

## 实现

针对 AffairQA 政务问答数据集，我们的实现方法遵循 KAG (Knowledge-Augmented Generation) 框架，具体步骤如下：
### 数据预处理与 Schema 定义
我们首先对 AffairQA 提供的原始政务数据进行预处理。在此阶段，我们可能会利用数据中固有的标签或其他特征（如您提到的 "label features"）对信息进行初步的归类或结构化整理，以便于后续的图谱构建。
基于 KAG 框架和 OpenSPG 的 schema 建模规范，我们对政务领域的核心概念（如政策文件、执行机构、服务事项、申请条件等）进行抽象，定义相应的实体类型（Entity Types）、关系类型（Relation Types）及其属性（Properties）。这份定义体现在 schema/AffairQA.schema 文件中，并被提交到 OpenSPG 图数据库，作为知识图谱的结构蓝图。
### 知识图谱构建
利用 builder/indexer.py 脚本执行知识图谱的构建过程。该脚本读取预处理后的数据，依据 AffairQA.schema 的定义：
识别并实例化政务实体（例如，具体的某项政策、某个部门）。
建立实体间的关联，即“链指”对应的关系类型（例如，“某政策” 发布机构 “某部门”，“某服务” 需要材料 “某证明”）。
将各个实体和关系对应的属性信息（如政策的发布日期、机构的联系方式等）写入 OpenSPG 图数据库。
通过这个过程，我们将分散的政务信息整合为结构化的知识图谱，存储在图存中。
### 基于 KAG 的问答实现
遵循 kag_config.yaml 中定义的 kag_solver_pipeline。此流程整合了 KAG 的核心组件能力：
规划器 (Planner - kag_static_planner): 接收到政务问题后，Planner 利用配置的大语言模型和 retriever_static_planning 提示模板，对问题进行深入分析，理解其核心意图。Planner 还可以借助 default_query_rewrite 提示对查询进行优化改写，最终生成一个结构化的检索计划，明确了从知识图谱中获取答案所需查询的具体信息节点和路径。
执行器/推理器 (Executor/Reasoner - *reasoner_conf): 该组件严格依照 Planner 输出的检索计划，作为与 OpenSPG 政务知识图谱交互的接口。它负责执行具体的查询操作，在图谱中高效导航，精准地检索和抽取回答问题所需的事实依据。
生成器 (Generator - llm_generator_with_thought): Generator 接收由 Executor/Reasoner 检索到的结构化事实信息。它再次调用大语言模型，将这些事实片段进行整合、推理，并结合问题的上下文，生成一个流畅、准确且信息丰富的自然语言答案。llm_generator_with_thought 类型表明其在生成答案的同时，也能阐述其内部的推理过程（thought）。
最终，系统产出的答案将通过 evaluate_qa.py 和 count_correct.py 脚本，与 AffairQA 数据集的标准答案进行比对，计算 Exact Match (EM) 和 F1 Score 指标，以此来量化评估整个 KAG 问答流程的性能和效果。



## 1. 前置条件

参考文档 [快速开始](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) 安装 KAG 及其依赖的 OpenSPG server，了解开发者模式 KAG 的使用流程。

## 2. 复现步骤

### Step 1：进入示例目录

```bash
cd kag/open_benchmark/AffairQA
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

执行以下命令提交 schema [AffairQA.schema](./schema/AffairQA.schema)。

```bash
knext schema commit
```

### Step 5：构建知识图谱

在 [builder](./builder) 目录执行 [indexer.py](./builder/indexer.py) 构建知识图谱。

```bash
cd builder && python indexer.py && cd ..
```

### Step 6：执行 QA 任务

在 [solver](./solver) 目录执行 [eval.py](./solver/eval.py) 生成答案并计算 EM 和 F1 指标。

```bash
cd solver && python eval.py && cd ..
```

生成的答案被保存至 ``./solver/data/res*.json``.

执行答案判断及F1和EM计算：
```bash
python solver/evalForAffairQA.py --input_file {eval 生成的答案}
``` 

### Step 7：（可选）清理

若要删除 checkpoint，可执行以下命令。

```bash
rm -rf ./builder/ckpt
rm -rf ./solver/ckpt
```

