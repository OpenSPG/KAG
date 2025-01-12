# KAG Example: Enterprise Supply Chain Knowledge Graph (SupplyChain)

[English](./README.md) |
[简体中文](./README_cn.md)

## 1. Background

Credit institutions conduct comprehensive analysis of a company's financial condition, operating condition, market position, and management capabilities, and assign a rating grade to reflect the credit status of the company, in order to support credit business. In practice, it heavily relies on the information provided by the evaluated company itself, such as annual reports, various qualification documents, asset proofs, etc. This type of information can only provide micro-level information about the company itself and cannot reflect the company's market situation along the entire industry chain or obtain information beyond what is proven.

This example is based on the SPG framework to construct an industry chain enterprise Knowledge graph and extract in-depth information between companies based on the industry chain, to support company credit ratings.

## 2. Overview

Please refer to the document for knowledge modeling: [Schema of Enterprise Supply Chain Knowledge Graph](./schema/README.md), As shown in the example below:

![KAG SupplyChain Schema Diagram](/_static/images/examples/supplychain/kag-supplychain-schema-diag.gif)

Concept knowledge maintains industry chain-related data, including hierarchical relations, supply relations. Entity instances consist of only legal representatives and transfer information. Company instances are linked to product instances based on the attributes of the products they produce, enabling deep information mining between company instances, such as supplier relationships, industry peers, and shared legal representatives. By leveraging deep contextual information, more credit assessment factors can be provided.

![KAG SupplyChain Event Diagram](/_static/images/examples/supplychain/kag-supplychain-event-diag.gif)

Within the industrial chain, categories of product and company events are established. These categories are a combination of indices and trends. For example, an increase in price consists of the index "价格" (price) and the trend "上涨" (rising). Causal knowledge sets the events of a company's profit decrease and cost increase due to a rise in product prices. When a specific event occurs, such as a significant increase in rubber prices, it is categorized under the event of a price increase. As per the causal knowledge, a price increase in a product leads to two event types: a decrease in company profits and an increase in company costs. Consequently, new events are generated:"三角\*\*轮胎公司成本上涨事件" and "三角\*\*轮胎公司利润下跌".

## 3. Quick Start

### 3.1 Precondition

Please refer to [Quick Start](https://openspg.yuque.com/ndx6g9/cwh47i/rs7gr8g4s538b1n7) to install KAG and its dependency OpenSPG server, and learn about using KAG in developer mode.

### 3.2 Steps to reproduce

#### Step 1: Enter the example directory

```bash
cd kag/examples/supplychain
```

#### Step 2: Configure models

Update the generative model configurations ``openie_llm`` and ``chat_llm`` in [kag_config.yaml](./kag_config.yaml).

You need to fill in correct ``api_key``s. If your model providers and model names are different from the default values, you also need to update ``base_url`` and ``model``.

Since the representational model is not used in this example, you can retain the default configuration for the representative model ``vectorize_model``.

#### Step 3: Project initialization

Initiate the project with the following command.

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

#### Step 4: Create knowledge schema

The schema file has been created and you can execute the following command to submit it:

```bash
knext schema commit
```

Submit the *leadto* relationship logical rules:

```bash
knext schema reg_concept_rule --file ./schema/concept.rule
```

You can refer to [Schema of Enterprise Supply Chain Knowledge Graph](./schema/README.md) for detailed information on schema modeling.

#### Step 5: Knowledge graph construction

Knowledge construction involves importing data into the knowledge graph storage. For data introduction, please refer to the document: [Introduction to Data of Enterprise Supply Chain](./builder/data/README.md).

In this example, we will demonstrate the conversion of structured data and entity linking. For specific details, please refer to the document: [Enterprise Supply Chain Case Knowledge Graph Construction](./builder/README.md).

Submit the knowledge importing tasks.

```bash
cd builder && python indexer.py && cd ..
```

#### Step 6: Executing query tasks for knowledge graph

OpenSPG supports the ISO GQL syntax. You can use the following command-line to execute a query task:

```bash
knext reasoner execute --dsl "${ql}"
```

For specific task details, please refer to the document: [Enterprise Credit Graph Query Tasks in Supply Chain](./reasoner/README.md).

Querying Credit Rating Factors:

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

Analyzing the Impact of an Event:

```bash
knext reasoner execute --dsl "
MATCH
    (s:SupplyChain.ProductChainEvent)-[:leadTo]->(o:SupplyChain.CompanyEvent)
RETURN
    s.id, s.subject, o.subject, o.name
"
```

#### Step 7: Execute DSL and QA tasks


```bash
python ./solver/qa.py
```

