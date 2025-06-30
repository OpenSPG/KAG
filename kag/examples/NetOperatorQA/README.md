# KAG NetOperatorQA

[English](./README_en.md) |
[简体中文](./README.md)

NetOperatorQA是一个专注于电信运营商领域的知识问答数据集。在数字化转型和智能通信服务快速发展的时代，电信运营商的业务范围不断扩展，涵盖5G网络建设、云计算服务、大数据应用、物联网业务、数字政府等多个领域。知识图谱（Knowledge Graph, KG）作为一种结构化信息管理方式，通过语义关联和语境理解，为运营商业务提供了全面的事实和数据支持。在涉及复杂技术文档、年度报告、业务规范和运营数据时，快速而准确的信息检索能力显得尤为重要。

本数据集专注于运营商知识问答任务，旨在从运营商相关的大型知识图谱中检索出业务事实，来回答相关问题。我们设定输入为一个特定的运营商业务问题，输出则是从知识图谱中提取到的用于回答问题的事实。数据来源包括运营商年度报告、季度报告、技术白皮书、业务介绍文档等多种形式的Markdown文档。

本例我们展示为NetOperatorQA数据集构建知识图谱，然后用[KAG](https://arxiv.org/abs/2409.13731)为评估问题生成答案，并与标准答案对比计算EM和F1指标。

## 实现

针对NetOperatorQA运营商知识问答数据集，我们的实现方法遵循KAG (Knowledge-Augmented Generation)框架，具体步骤如下：

### 数据预处理与Schema定义
我们首先对NetOperatorQA提供的原始运营商数据进行预处理。在此阶段，我们处理运营商年度报告、技术文档、业务介绍等多种格式的Markdown文档，对信息进行初步的归类或结构化整理，以便于后续的图谱构建。

基于KAG框架和OpenSPG的schema建模规范，我们对运营商领域的核心概念（如网络技术、业务产品、财务数据、技术指标、合作伙伴等）进行抽象，定义相应的实体类型（Entity Types）、关系类型（Relation Types）及其属性（Properties）。这份定义体现在schema/NetOperatorQA.schema文件中，并被提交到OpenSPG图数据库，作为知识图谱的结构蓝图。



## 1. 前置条件

参考文档 [快速开始](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) 安装KAG及其依赖的OpenSPG server，了解开发者模式KAG的使用流程。

## 配置说明

### 索引构建配置
在配置文件中，你可以根据需要启用不同的提取器组合：

**完整索引构建（推荐用于生产环境）**：
- chunk_extractor - 基础文本块
- outline_extractor - 大纲结构  
- summary_extractor - 语义摘要
- table_extractor - 表格数据
- atomic_query_extractor - 原子查询

**快速构建（适用于测试和开发）**：
- 仅使用基础文本块提取器

### 检索配置选择
系统提供两种主要的检索配置：

**简单检索模式**：适用于直接事实查询
- 仅使用向量检索器，快速响应

**完整检索模式**：适用于复杂推理查询
- 原子查询检索器
- 大纲检索器
- 摘要检索器
- 向量检索器
- 表格检索器



## 2. 复现步骤

### Step 1：进入示例目录

```bash
cd kag/examples/NetOperatorQA
```

### Step 2：配置模型

更新 [kag_config.yaml](./kag_config.yaml) 中的生成模型配置 `openie_llm` 和 `chat_llm` 和表示模型配置 `vectorize_model`。

您需要设置正确的 `api_key`。如果使用的模型供应商和模型名与默认值不同，您还需要更新 `base_url` 和 `model`。

### Step 3：初始化项目

先对项目进行初始化。

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### Step 4：提交schema

执行以下命令提交schema [NetOperatorQA.schema](./schema/NetOperatorQA.schema)。

```bash
knext schema commit
```

### Step 5：构建知识图谱

在 [builder](./builder) 目录执行 [indexer.py](./builder/indexer.py) 构建知识图谱。

```bash
cd builder && python indexer.py && cd ..
```

### Step 6：执行QA任务

在 [solver](./solver) 目录执行 [eval.py](./solver/eval.py) 生成答案并计算EM和F1指标。

```bash
cd solver && python eval.py && cd ..
```



### Step 7：（可选）清理

若要删除checkpoint，可执行以下命令。

```bash
rm -rf ./builder/ckpt
rm -rf ./solver/ckpt
```

## 数据集与技术特点

### 数据集特点
NetOperatorQA数据集具有以下特点：

1. **多文档类型**: 包含年度报告(AY系列)、技术白皮书(BZ系列)、业务介绍(BY系列)、网络建设(BW系列)、技术标准(BT系列)、财务数据(BF系列)等多种类型的文档

2. **丰富的业务领域**: 涵盖5G网络、云计算、大数据、物联网、工业互联网、数字政府、智慧城市等运营商核心业务领域

3. **结构化信息**: 包含财务指标、技术参数、业务数据、合作关系等多维度的结构化信息

4. **时序性**: 数据涵盖多个时间段的报告和数据，便于进行趋势分析和历史对比

5. **专业性**: 涉及电信技术术语、业务模式、财务指标等专业内容，对模型的领域理解能力提出较高要求

### 技术架构特点

1. **多重索引体系**: 构建了文本块索引、大纲索引、摘要索引、表格索引、原子查询索引等多种索引类型

2. **混合检索策略**: 结合向量检索、结构化检索、语义检索等多种检索方法

3. **自适应推理**: 根据问题复杂度自动选择简单推理器或复杂推理器

4. **领域优化**: 针对运营商领域特点定制了专用规划器和提示模板

5. **可配置架构**: 支持灵活配置不同的提取器、检索器和推理器组合

6. **性能优化**: 提供快速模式和完整模式，平衡效果与效率
