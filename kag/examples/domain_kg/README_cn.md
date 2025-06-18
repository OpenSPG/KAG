# KAG 示例：DomainKG

[English](./README.md) |
[简体中文](./README_cn.md)

本示例提供了一个医疗领域知识注入的案例，其中领域知识图谱的节点为医学名词，关系为 isA。文档内容为部分医学名词的介绍。


## 1. 前置条件

参考文档 [快速开始](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) 安装 KAG 及其依赖的 OpenSPG server，了解开发者模式 KAG 的使用流程。

## 2. 复现步骤

### Step 1：进入示例目录

```bash
cd kag/examples/domain_kg
```

### Step 2：配置模型

更新 [kag_config.yaml](./kag_config.yaml) 中的生成模型配置 ``openie_llm`` 和 ``chat_llm`` 和表示模型配置 ``vectorizer_model``。

您需要设置正确的 ``api_key``。如果使用的模型供应商和模型名与默认值不同，您还需要更新 ``base_url`` 和 ``model``。

### Step 3：初始化项目

先对项目进行初始化。

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### Step 4：提交 schema

执行以下命令提交 schema [DomainKG.schema](./schema/DomainKG.schema)。

```bash
knext schema commit
```

### Step 5：构建知识图谱

我们首先需要将领域知识图谱注入到图数据库中，这样在对非结构化文档进行图谱构建的时候，PostProcessor 组件可以将抽取出的节点与领域知识图谱节点进行链指（标准化）。
在 [builder](./builder) 目录执行 [injection.py](./builder/injection.py) ，注入图数据。

```bash
cd builder && python injection.py && cd ..
```

注意，KAG为领域知识图谱注入提供了一个特殊的 ``KAGBuilderChain`` 实现，即 ``DomainKnowledgeInjectChain``，其注册名为 ``domain_kg_inject_chain``。由于领域知识注入不涉及到扫描文件或目录，可以直接调用 builder chain 的 ``invoke`` 接口启动任务。

接下来，在 [builder](./builder) 目录执行 [indexer.py](./builder/indexer.py) 构建知识图谱。

```bash
cd builder && python indexer.py && cd ..
```

### Step 6：执行 QA 任务

在 [solver](./solver) 目录执行 [qa.py](./solver/qa.py) 生成问题的答案。

```bash
cd solver && python qa.py && cd ..
```

### Step 7：（可选）清理

若要删除 checkpoint，可执行以下命令。

```bash
rm -rf ./builder/ckpt
rm -rf ./solver/ckpt
```

