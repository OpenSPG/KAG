# KAG 示例：医疗图谱（Medicine）

[English](./README.md) |
[简体中文](./README_cn.md)

本示例旨在展示如何基于 schema 的定义，利用大模型实现对图谱实体和关系的抽取和构建到图谱。

![KAG Medicine Diagram](/_static/images/examples/medicine/kag-medicine-diag.png)

## 1. 前置条件

参考文档 [快速开始](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) 安装 KAG 及其依赖的 OpenSPG server，了解开发者模式 KAG 的使用流程。

## 2. 复现步骤

### Step 1：进入示例目录

```bash
cd kag/examples/medicine
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

执行以下命令提交医疗图谱 schema [Medicine.schema](./schema/Medicine.schema)。

```bash
knext schema commit
```

### Step 5：构建知识图谱

在 [builder](./builder) 目录执行 [indexer.py](./builder/indexer.py) 通过领域知识导入和 schema-free 抽取构建知识图谱。

```bash
cd builder && python indexer.py && cd ..
```

您可以检查 [Disease.csv](./builder/data/Disease.csv) 查看疾病的描述，我们通过定义在 [kag_config.yaml](./kag_config.yaml) 的 ``extract_runner`` 对这些无结构文本描述做 schema-free 抽取。

[data](./builder/data) 中的其他结构化数据通过定义在 [kag_config.yaml](./kag_config.yaml) 中的相应 KAG builder chain 直接导入。

### Step 6：使用 GQL 查询知识图谱

您可以使用 ``knext reasoner`` 命令检查构建的知识图谱。查询 DSL 将由 OpenSPG server 执行，它支持 ISO GQL。

* 使用以下命令直接执行 DSL。

  ```bash
  knext reasoner execute --dsl "
  MATCH
      (s:Medicine.HospitalDepartment)-[p]->(o)
  RETURN
      s.id, s.name
  "
  ```

  查询结果会显示在屏幕上并以 CSV 格式保存到当前目录。

* 您也可以将 DSL 保存到文件，然后通过文件提交 DSL。

  ```bash
  knext reasoner execute --file ./reasoner/rule.dsl
  ```

* 您还可以使用 reasoner 的 Python 客户端查询知识图谱。

  ```bash
  python ./reasoner/client.py
  ```

### Step 7：执行 QA 任务

在 [solver](./solver) 目录执行 [evaForMedicine.py](./solver/evaForMedicine.py) 用自然语言问一个示例问题并查看答案和 trace log。

```bash
cd solver && python evaForMedicine.py && cd ..
```

### Step 8：（可选）清理

若要删除 checkpoint，可执行以下命令。

```bash
rm -rf ./builder/ckpt
```

