# 基于 SPG 建模的产业链企业图谱

[English](./README.md) |
[简体中文](./README_cn.md)

## 1. 建模文件

schema 文件语法介绍参见 [声明式 schema](https://openspg.yuque.com/ndx6g9/0.6/fzhov4l2sst6bede)。

企业供应链图谱 schema 建模参考文件 [SupplyChain.schema](./SupplyChain.schema)。

执行以下脚本，完成 schema 创建：

```bash
knext schema commit
```

## 2. SPG 建模方法 vs 属性图建模方法

本节对比 SPG 语义建模和普通建模的差异。

### 2.1 语义属性 vs 文本属性

假定存在如下公司信息："北大药份限公司"生产的产品有四个"医疗器械批发,医药批发,制药,其他化学药品"。

```text
id,name,products
CSF0000000254,北大*药*份限公司,"医疗器械批发,医药批发,制药,其他化学药品"
```

#### 2.1.1 基于文本属性建模

```text
//文本属性建模
Company(企业): EntityType
    properties:
        product(经营产品): Text
```

此时经营产品只为文本，不包含语义信息，是无法得到“北大药份限公司”的上下游产业链相关信息，极不方便维护也不方便使用。

#### 2.1.2 基于关系建模

```text
Product(产品): EntityType
    properties:
        name(产品名): Text
    relations:
        isA(上位产品): Product

Company(企业): EntityType
    relations:
        product(经营产品): Product
```

但如此建模，则需要将数据分为 3 列：

```text
id,name,product
CSF0000000254,北大*药*份限公司,医疗器械批发
CSF0000000254,北大*药*份限公司,医药批发
CSF0000000254,北大*药*份限公司,制药
CSF0000000254,北大*药*份限公司,其他化学药品
```

这种方式也存在两个缺点：

1. 原始数据需要做一次清洗，转换成多行。

2. 需要新增维护关系数据，当原始数据发生变更时，需要删除原有关系，再新增数据，容易导致数据错误。

#### 2.1.3 基于 SPG 语义属性建模

SPG 支持语义属性，可简化知识构建，如下：

```text
Product(产品): ConceptType
    hypernymPredicate: isA

Company(企业): EntityType
    properties:
        product(经营产品): Product
            constraint: MultiValue
```

企业中具有一个经营产品属性，且该属性的类型为 ``Product`` 类型，只需将如下数据导入，可自动实现属性到关系的转换。

```text
id,name,products
CSF0000000254,北大*药*份限公司,"医疗器械批发,医药批发,制药,其他化学药品"
```

### 2.2 逻辑表达的属性、关系 vs 数据表达的属性、关系

假定需要得到企业所在行业，根据当前已有数据，可执行如下查询语句：

```cypher
MATCH
    (s:Company)-[:product]->(o:Product)-[:belongToIndustry]->(i:Industry)
RETURN
    s.id, i.id
```

该方式需要熟悉图谱 schema，对人员上手要求比较高，故也有一种实践是将这类属性重新导入图谱，如下：

```text
Company(企业): EntityType
    properties:
        product(经营产品): Product
            constraint: MultiValue
    relations:
        belongToIndustry(所在行业): Industry
```

新增一个关系类型，来直接获取公司所属行业信息。

这种方式缺点主要有两个：

1. 需要用户手动维护新增关系数据，增加使用维护成本。

2. 由于新关系和图谱数据存在来源依赖，非常容易导致图谱数据出现不一致问题。

针对上述缺点，SPG 支持逻辑表达属性和关系，如下建模方式：

```text
Company(企业): EntityType
    properties:
        product(经营产品): Product
            constraint: MultiValue
    relations:
        belongToIndustry(所在行业): Industry
            rule: [[
                Define (s:Company)-[p:belongToIndustry]->(o:Industry) {
                    Structure {
                        (s)-[:product]->(c:Product)-[:belongToIndustry]->(o)
                    }
                    Constraint {
                    }
                }
            ]]
```

具体内容可参见 [产业链企业信用图谱查询任务](../reasoner/README_cn.md) 中场景 1、场景 2 的示例。

### 2.3 概念体系 vs 实体体系

现有图谱方案也有常识图谱，例如 ConceptNet 等，但在业务落地中，不同业务有各自体现业务语义的类目体系，基本上不存在一个常识图谱可应用到所有业务场景，故常见的实践为将业务领域体系创建为实体，和其他实体数据混用，这就导致在同一个分类体系上，既要对 schema 的扩展建模，又要对语义上的细分类建模，数据结构定义和语义建模的耦合，导致工程实现及维护管理的复杂性，也增加了业务梳理和表示(认知)领域知识的困难。

SPG 区分了概念和实体，用于解耦语义和数据，如下：

```text
Product(产品): ConceptType
    hypernymPredicate: isA

Company(企业): EntityType
    properties:
        product(经营产品): Product
            constraint: MultiValue
```

产品被定义为概念，公司被定义为实体，相互独立演进，两者通过 SPG 提供的语义属性进行挂载关联，用户无需手动维护企业和产品之间关联。

### 2.4 事件时空多元表达

事件多要素结构表示也是一类超图（HyperGrpah）无损表示的问题，它表达的是时空多元要素的时空关联性，事件是各要素因某种行为而产生的临时关联，一旦行为结束，这种关联也随即消失。在以往的属性图中，事件只能使用实体进行替代，由文本属性表达事件内容，如下类似事件：

![KAG SupplyChain Event Demo](/_static/images/examples/supplychain/kag-supplychain-event-demo.png)

```text
Event(事件):
    properties:
        eventTime(发生时间): Long
        subject(涉事主体): Text
        object(客体): Text
        place(地点): Text
        industry(涉事行业): Text
```

这种表达方式，是无法体现真实事件的多元关联性，SPG 提供了事件建模，可实现事件多元要素的关联，如下：

```text
CompanyEvent(公司事件): EventType
    properties:
        subject(主体): Company
        index(指标): Index
        trend(趋势): Trend
        belongTo(属于): TaxOfCompanyEvent
```

上述的事件中，属性类型均为已被定义类型，没有基本类型表达，SPG 基于此申明实现事件多元要素表达，具体应用示例可见 [产业链企业信用图谱查询任务](../reasoner/README_cn.md) 中场景 3 的具体描述。

