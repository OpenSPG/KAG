# KAG 示例：企业供应链（SupplyChain）

[English](./README.md) |
[简体中文](./README_cn.md)

## 1. 背景

信贷机构对企业的财务状况、经营状况、市场地位、管理能力等进行综合分析，给予企业一个评级等级，反映其信用状况的好坏，以便支撑信贷业务。在实践中基本依赖被评估企业自身提供的信息，例如企业年报、各类资质文件、资产证明等，这一类信息只能围绕企业自身提供微观层面的信息，不能体现企业在整个产业链上下游市场情况，也无法得到证明之外的信息。

本例基于 SPG 构建产业链企业图谱，挖掘出企业之间基于产业链的深度信息，支持企业信用评级。

## 2. 总览

建模参考 [基于 SPG 建模的产业链企业图谱](./schema/README_cn.md)，如下图示意。

![KAG SupplyChain Schema Diagram](/_static/images/examples/supplychain/kag-supplychain-schema-diag.gif)

概念知识维护着产业链相关数据，包括上下位层级、供应关系；实体实例仅有法人代表、转账信息，公司实例通过生产的产品属性和概念中的产品节点挂载，实现了公司实例之间的深度信息挖掘，例如供应商、同行业、同法人代表等关系。基于深度上下文信息，可提供更多的信用评估因子。

![KAG SupplyChain Event Diagram](/_static/images/examples/supplychain/kag-supplychain-event-diag.gif)

产业链中建立了产品和公司事件类别，该类别属于指标和趋势的一种组合，例如价格上涨，是由指标：价格，趋势：上涨两部分构成。

事理知识设定了产品价格上涨引起公司利润下降及公司成本上涨事件，当发生某个具体事件时，例如“橡胶价格大涨事件”，被归类在产品价格上涨，由于事理知识中定义产品价格上涨会引起公司利润下降/公司成本上涨两个事件类型，会产出新事件：“三角\*\*轮胎公司成本上涨事件”、“三角\*\*轮胎公司利润下跌”。

## 3. Quick Start

### 3.1 前置条件

请参考文档 [快速开始](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) 安装 KAG 及其依赖的 OpenSPG server，并了解开发者模式 KAG 的使用流程。

### 3.2 复现步骤

#### Step 1：进入示例目录

```bash
cd kag/examples/supplychain
```

#### Step 2：配置模型

更新 [kag_config.yaml](./kag_config.yaml) 中的生成模型配置 ``openie_llm`` 和 ``chat_llm``。

您需要设置正确的 ``api_key``。如果使用的模型供应商和模型名与默认值不同，您还需要更新 ``base_url`` 和 ``model``。

在本示例中未使用表示模型，可保持表示模型配置 ``vectorize_model`` 的默认配置。

#### Step 3：初始化项目

先对项目进行初始化。

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

#### Step 4：知识建模

schema 文件已创建好，可执行如下命令提交。

```bash
knext schema commit
```

提交 *leadto* 关系逻辑规则。

```bash
knext schema reg_concept_rule --file ./schema/concept.rule
```

schema 建模详细内容可参见 [基于 SPG 建模的产业链企业图谱](./schema/README_cn.md)。

#### Step 5：知识构建

知识构建将数据导入到系统中，数据介绍参见文档 [产业链案例数据介绍](./builder/data/README_cn.md)。

本例主要为结构化数据，故演示结构化数据转换和实体链指，具体细节可参见文档 [产业链案例知识构建](./builder/README_cn.md)。

提交知识构建任务导入数据。

```bash
cd builder && python indexer.py && cd ..
```

#### Step 6：执行图谱任务

SPG 支持 ISO GQL 语法，可用如下命令行执行查询任务。

```bash
knext reasoner execute --dsl "${ql}"
```

具体任务详情可参见文档 [产业链企业信用图谱查询任务](./reasoner/README_cn.md)。

查询信用评级因子：

```bash
knext reasoner execute --dsl "
MATCH
    (s:SupplyChain.Company)
RETURN
    s.id, s.name, s.fundTrans1Month, s.fundTrans3Month,
    s.fundTrans6Month, s.fundTrans1MonthIn, s.fundTrans3MonthIn,
    s.fundTrans6MonthIn, s.cashflowDiff1Month, s.cashflowDiff3Month,
    s.cashflowDiff6Month
"
```

```bash
knext reasoner execute --dsl "
MATCH
    (s:SupplyChain.Company)-[:mainSupply]->(o:SupplyChain.Company)
RETURN
    s.name, o.name
"
```

```bash
knext reasoner execute --dsl "
MATCH
    (s:SupplyChain.Company)-[:belongToIndustry]->(o:SupplyChain.Industry)
RETURN
    s.name, o.name
"
```

```bash
knext reasoner execute --dsl "
MATCH
    (s:SupplyChain.Company)-[:sameLegalRepresentative]->(o:SupplyChain.Company)
RETURN
    s.name, o.name
"
```

事件影响分析：

```bash
knext reasoner execute --dsl "
MATCH
    (s:SupplyChain.ProductChainEvent)-[:leadTo]->(o:SupplyChain.CompanyEvent)
RETURN
    s.id, s.subject, o.subject, o.name
"
```

#### Step 7：执行 DSL 及 QA 任务

```bash
python ./solver/qa.py
```

