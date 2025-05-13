# 1. KAG 是什么

KAG 是基于 [OpenSPG](https://github.com/OpenSPG/openspg) 引擎和大型语言模型的逻辑推理问答框架，用于构建垂直领域知识库的逻辑推理问答解决方案。KAG 可以有效克服传统 RAG 向量相似度计算的歧义性和 OpenIE 引入的 GraphRAG 的噪声问题。KAG 支持逻辑推理、多跳事实问答等，并且明显优于目前的 SOTA 方法。

KAG 的目标是在专业领域构建知识增强的 LLM 服务框架，支持逻辑推理、事实问答等。KAG 充分融合了 KG 的逻辑性和事实性特点，其核心功能包括：

* 知识与 Chunk 互索引结构，以整合更丰富的上下文文本信息
* 利用概念语义推理进行知识对齐，缓解 OpenIE 引入的噪音问题
* 支持 Schema-Constraint 知识构建，支持领域专家知识的表示与构建
* 逻辑符号引导的混合推理与检索，实现逻辑推理和多跳推理问答

# 2. KAG 核心功能

## 2.1 LLM 友好的语义化知识管理

私域知识库场景，非结构化数据、结构化信息、业务专家经验 往往三者共存，KAG 提出了一种对大型语言模型（LLM）友好的知识表示框架，在 DIKW（数据、信息、知识和智慧）的层次结构基础上，将 SPG 升级为对 LLM 友好的版本，命名为 LLMFriSPG。

这使得它能够在同一知识类型（如实体类型、事件类型）上兼容无 schema 约束的信息提取和有 schema 约束的专业知识构建，并支持图结构与原始文本块之间的互索引表示。

这种互索引表示有助于基于图结构的倒排索引的构建，并促进了逻辑形式的统一表示、推理和检索。同时通过知识理解、语义对齐等进一步降低信息抽取的噪声，提升知识的准确率和一致性。


## 2.2 逻辑符号引导的混合推理引擎

KAG 提出了一种逻辑符号引导的混合求解和推理引擎。该引擎包括三种类型的运算符：规划、推理和检索，将自然语言问题转化为结合语言和符号的问题求解过程。

在这个过程中，每一步都可以利用不同的运算符，如精确匹配检索、文本检索、数值计算或语义推理，从而实现四种不同问题求解过程的集成：图谱推理、逻辑计算、Chunk 检索和 LLM 推理。

# 3. 版本发布

## 3.1 最近更新

* 2025.01.07 : 支持 领域知识注入、领域 schema 自定义、摘要生成类任务支持、可视化图分析查询、schema-constraint模式抽取等
* 2024.11.21 : 支持 Word 文档上传、知识库删除、模型调用并发度设置、用户体验优化等
* 2024.10.25 : KAG 首次发布

## 3.2 后续计划

* 逻辑推理 优化、对话式任务支持
* kag-model 发布、事理图谱 和 医疗图谱的 kag 解决方案发布
* kag 前端开源、分布式构建支持、数学推理 优化

# 4. 快速开始

## 4.1 基于产品（面向普通用户）

### 4.1.1 引擎&依赖 镜像安装

* **推荐系统版本：**

  ```text
  macOS 用户：macOS Monterey 12.6 或更新版本
  Linux 用户：CentOS 7 / Ubuntu 20.04 或更新版本
  Windows 用户：Windows 10 LTSC 2021 或更新版本
  ```

* **软件要求：**

  ```text
  macOS / Linux 用户：Docker，Docker Compose
  Windows 用户：WSL 2 / Hyper-V，Docker，Docker Compose
  ```

使用以下命令下载 docker-compose.yml 并用 Docker Compose 启动服务。

```bash
# 设置 HOME 环境变量（仅 Windows 用户需要执行）
# set HOME=%USERPROFILE%

curl -sSL https://raw.githubusercontent.com/OpenSPG/openspg/refs/heads/master/dev/release/docker-compose.yml -o docker-compose.yml
docker compose -f docker-compose.yml up -d
```

### 4.1.2 使用

具体使用请参考 [KAG使用(产品模式)](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17#JQH6Y)。

## 4.2 基于工具包（面向开发者）

### 4.2.1 引擎&依赖 镜像安装

参考 4.1 部分完成引擎&依赖的镜像安装。

### 4.2.2 KAG 安装

**macOS / Linux 开发者**

```text
# 安装 Python 虚拟环境：conda create -n kag-demo python=3.10 && conda activate kag-demo

# 代码 clone：git clone https://github.com/OpenSPG/KAG.git

# KAG 安装: cd KAG && pip install -e .
```

**Windows 开发者**

```
# 安装官方 Python 3.8.10 或更新版本，安装 Git。

# 创建、激活 Python 虚拟环境：py -m venv kag-demo && kag-demo\Scripts\activate

# 代码 clone：git clone https://github.com/OpenSPG/KAG.git

# KAG 安装: cd KAG && pip install -e .
```

### 4.2.3 使用

开发者可以参考 [KAG使用(开发者模式)](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17#MRgKi)，基于 KAG 内置的各种组件，实现内置数据集的效果复现 + 新场景的落地。



# 5. 技术架构

KAG 框架包括 kg-builder、kg-solver、kag-model 三部分。本次发布只涉及前两部分，kag-model 将在后续逐步开源发布。

kg-builder 实现了一种对大型语言模型（LLM）友好的知识表示，在 DIKW（数据、信息、知识和智慧）的层次结构基础上，升级 SPG 知识表示能力，在同一知识类型（如实体类型、事件类型）上兼容无 schema 约束的信息提取和有 schema 约束的专业知识构建，并支持图结构与原始文本块之间的互索引表示，为推理问答阶段的高效检索提供支持。

kg-solver 采用逻辑形式引导的混合求解和推理引擎，该引擎包括三种类型的运算符：规划、推理和检索，将自然语言问题转化为结合语言和符号的问题求解过程。在这个过程中，每一步都可以利用不同的运算符，如精确匹配检索、文本检索、数值计算或语义推理，从而实现四种不同问题求解过程的集成：检索、知识图谱推理、语言推理和数值计算。

# 6. 联系我们

**GitHub**: <https://github.com/OpenSPG/KAG>

**OpenSPG**: <https://spg.openkg.cn/>
