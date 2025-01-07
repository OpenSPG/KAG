# Enterprise Credit Graph Query Tasks in Supply Chain

[English](./README.md) |
[简体中文](./README_cn.md)

## Scenario 1: Generation of Enterprise Credit Rating Features

Requirement: In enterprise credit rating, the following decision factors are needed:

1. Primary supplier relations
2. Industry of the products produced by the enterprise
3. Transfer transaction records of funds for the past 1 month, 3 months, and 6 months
4. Difference in funds flow for the past 1 month, 3 months, and 6 months
5. Information on related companies controlled by the ultimate beneficial owner

However, in the original knowledge graph, only fund transfer transactions and legal representative information are available, making it impossible to directly obtain the above features. This example demonstrates how to use OpenSPG to obtain these 5 features.

The feature definitions are present in the schema file, which can be viewed by clicking [SupplyChain.schema](../schema/SupplyChain.schema).

**Feature 1: Defining primary supply chain relations between companies**

with the following rule definition:

```text
Define (s:Compnay)-[p:mainSupply]->(o:Company) {
    Structure {
        (s)-[:product]->(upProd:Product)-[:hasSupplyChain]->(downProd:Product)<-[:product]-(o),
        (o)-[f:fundTrans]->(s)
        (otherCompany:Company)-[otherf:fundTrans]->(s)
    }
    Constraint {
        // Compute the percentage of incoming transfers for company `o`
        otherTransSum("Total amount of incoming transfers") = group(s).sum(otherf.transAmt)
        targetTransSum("Total amount of transfers received by company o") = group(s,o).sum(f.transAmt)
        transRate = targetTransSum*1.0/(otherTransSum + targetTransSum)
        R1("The percentage must be over 50%"): transRate > 0.5
    }
}
```

**Feature 2: Industry of the Products Produced by the Enterprise**

```text
Define (s:Compnay)-[p:belongToIndustry]->(o:Industry) {
    Structure {
        (s)-[:product]->(c:Product)-[:belongToIndustry]->(o)
    }
    Constraint {
    }
}
```

**Feature 3: Transfer transaction records of funds for the past 1 month, 3 months, and 6 months**

```text
// Amount of outgoing transfers for the past 1 month
Define (s:Compnay)-[p:fundTrans1Month]->(o:Int) {
    Structure {
        (s)-[f:fundTrans]->(c:Company)
    }
    Constraint {
        R1("Transactions within the past 1 month"): date_diff(from_unix_time(now(), 'yyyyMMdd'),f.transDate) < 30
        totalOut = group(s).sum(transAmt)
        o = totalOut
    }
}

// Amount of outgoing transfers for the past 3 month
Define (s:Compnay)-[p:fundTrans3Month]->(o:Int) {
    Structure {
        (s)-[f:fundTrans]->(c:Company)
    }
    Constraint {
        R1("Transactions within the past 4 month"): date_diff(from_unix_time(now(), 'yyyyMMdd'),f.transDate) < 90
        totalOut = group(s).sum(transAmt)
        o = totalOut
    }
}

// Amount of outgoing transfers for the past 6 month
Define (s:Compnay)-[p:fundTrans6Month]->(o:Int) {
    Structure {
        (s)-[f:fundTrans]->(c:Company)
    }
    Constraint {
        R1("Transactions within the past 6 month"): date_diff(from_unix_time(now(), 'yyyyMMdd'),f.transDate) < 180
        totalOut = group(s).sum(transAmt)
        o = totalOut
    }
}

// Amount of incoming transfers for the past 1 month
Define (s:Compnay)-[p:fundTrans1MonthIn]->(o:Int) {
    Structure {
        (s)<-[f:fundTrans]-(c:Company)
    }
    Constraint {
        R1("Transactions within the past 1 month"): date_diff(from_unix_time(now(), 'yyyyMMdd'),f.transDate) < 30
        totalOut = group(s).sum(transAmt)
        o = totalOut
    }
}

// Amount of incoming transfers for the past 3 month
Define (s:Compnay)-[p:fundTrans3MonthIn]->(o:Int) {
    Structure {
        (s)<-[f:fundTrans]-(c:Company)
    }
    Constraint {
        R1("Transactions within the past 3 month"): date_diff(from_unix_time(now(), 'yyyyMMdd'),f.transDate) < 90
        totalOut = group(s).sum(transAmt)
        o = totalOut
    }
}

// Amount of incoming transfers for the past 6 month
Define (s:Compnay)-[p:fundTrans6MonthIn]->(o:Int) {
    Structure {
        (s)<-[f:fundTrans]-(c:Company)
    }
    Constraint {
        R1("Transactions within the past 6 month"): date_diff(from_unix_time(now(), 'yyyyMMdd'),f.transDate) < 180
        totalOut = group(s).sum(transAmt)
        o = totalOut
    }
}
```

**Feature 4: Difference in funds flow for the past 1 month, 3 months, and 6 months**

```text
// Funds flow difference in the past 1 month
Define (s:Company)-[p:cashflowDiff1Month]->(o:Integer) {
    Structure {
        (s)
    }
    Constraint {
        // Refer to the rule in Feature 3
        fundTrans1Month = rule_value(s.fundTrans1Month == null, 0, s.fundTrans1Month)
        fundTrans1MonthIn = rule_value(s.fundTrans1MonthIn == null, 0, s.fundTrans1MonthIn)
        o = fundTrans1Month - fundTrans1MonthIn
    }
}

// Funds flow difference in the past 3 month
Define (s:Company)-[p:cashflowDiff3Month]->(o:Integer) {
    Structure {
        (s)
    }
    Constraint {
        // Refer to the rule in Feature 3
        fundTrans3Month = rule_value(s.fundTrans3Month == null, 0, s.fundTrans3Month)
        fundTrans3MonthIn = rule_value(s.fundTrans3MonthIn == null, 0, s.fundTrans3MonthIn)
        o = fundTrans3Month - fundTrans3MonthIn
    }
}


// Funds flow difference in the past 6 month
Define (s:Company)-[p:cashflowDiff6Month]->(o:Integer) {
    Structure {
        (s)
    }
    Constraint {
        fundTrans6Month = rule_value(s.fundTrans6Month == null, 0, s.fundTrans6Month)
        fundTrans6MonthIn = rule_value(s.fundTrans6MonthIn == null, 0, s.fundTrans6MonthIn)
        o = fundTrans6Month - fundTrans6MonthIn
    }
}
```

**Feature 5: Information on related companies controlled by the ultimate beneficial owner**

```text
// Definition of the "same legal reprensentative" relation
Define (s:Compnay)-[p:sameLegalReprensentative]->(o:Company) {
    Structure {
        (s)<-[:legalReprensentative]-(u:Person)-[:legalReprensentative]->(o)
    }
    Constraint {
    }
}
```

Obtaining specific features of a particular company through GQL using the following query:

```cypher
MATCH
    (s:SupplyChain.Company)
RETURN
    s.id, s.fundTrans1Month, s.fundTrans3Month,
    s.fundTrans6Month, s.fundTrans1MonthIn, s.fundTrans3MonthIn,
    s.fundTrans6MonthIn, s.cashflowDiff1Month, s.cashflowDiff3Month, s.cashflowDiff6Month
```

```cypher
MATCH
    (s:SupplyChain.Company)-[:mainSupply]->(o:SupplyChain.Company)
RETURN
    s.id, o.id
```

```cypher
MATCH
    (s:SupplyChain.Company)-[:belongToIndustry]->(o:SupplyChain.Industry)
RETURN
    s.id, o.id
```

```cypher
MATCH
    (s:SupplyChain.Company)-[:sameLegalRepresentative]->(o:SupplyChain.Company)
RETURN
    s.id, o.id
```

## Scenario 2: Change in the company's supply chain

Suppose that there is a change in the products produced by the company：

```text
"钱****份限公司"发布公告，生产产品“三轮摩托车，二轮摩托车”变更为“两轮摩托车”，则"三角**轮胎股份"和钱"****份限公司"的主供应链关系自动断裂，"三角**轮胎股份"和"钱****份限公司"不再具有主供应链关系
```

The updated data is available in ``CompanyUpdate.csv``:

```text
id,name,products
CSF0000001662,浙江**摩托**限公司,"汽车-摩托车制造-二轮摩托车"
```

resubmit the building task：

```bash
knext builder execute CompanyUpdate
```

After the execution is completed, if you query again, only the Two-Wheeled Motorcycle will be returned, and the Three-Wheeled Motorcycle will no longer be associated.

```cypher
MATCH
    (s:SupplyChain.Company)-[:product]->(o:SupplyChain.Product)
WHERE
    s.id = "CSF0000001662"
RETURN
    s.id, o.id
```

## Scenario 3: Impact on the Supply Chain Event

The event details are as follows:

```text
id,name,subject,index,trend
1,顺丁橡胶成本上涨,商品化工-橡胶-合成橡胶-顺丁橡胶,价格,上涨
```

submit the building task of the event type:

```bash
knext builder execute ProductChainEvent
```

The transmission linkages are as follows:

![KAG SupplyChain Product Chain Demo](/_static/images/examples/supplychain/kag-supplychain-product-chain-demo-en.gif)

Butadiene rubber costs rise, classified as an event of price increase in the supply chain.

The logical rule expression is as follows:

```text
// When the attributes of ProductChainEvent satisfy the condition of price increase,
// the event is classified as a price increase event.
Define (e:ProductChainEvent)-[p:belongTo]->(o:`TaxonofProductChainEvent`/`价格上涨`) {
    Structure {
    }
    Constraint {
        R1: e.index == '价格'
        R2: e.trend == '上涨'
    }
}
```

Price increase in the supply chain, under the following conditions, will result in cost rise for specific companies.

```text
// The rules for price increase and increase in company costs are defined as follows.
Define (s:`TaxonofProductChainEvent`/`价格上涨`)-[p:leadTo]->(o:`TaxonofCompanyEvent`/`成本上涨`) {
    Structure {
        //1. Find the subject of the supply chain event, which is butadiene rubber in this case
        //2. Identify the downstream products of butadiene rubber, which are bias tires in this case
        //3. Identify all the companies that produce bias tires, which is "Triangle** Tire Co., Ltd." in this case
        (s)-[:subject]->[prod:Product]-[:hasSupplyChain]->(down:Product)<-[:product]-(c:Company)
    }
    Constraint {
    }
    Action {
        // Create a company cost increase event with the subject being the obtained "Triangle** Tire Co., Ltd."
        downEvent = createNodeInstance(
            type=CompanyEvent,
            value={
                subject=c.id
                trend="上涨"
                index="成本"
            }
        )
        // Since this event is caused by a price increase in the supply chain, add an edge between them.
        createEdgeInstance(
            src=s,
            dst=downEvent,
            type=leadTo,
            value={
            }
        )
    }
}
```

You can find the impact of a specific event by using the following query statement.

```cypher
MATCH
    (s:SupplyChain.ProductChainEvent)-[:leadTo]->(o:SupplyChain.CompanyEvent)
RETURN
    s.id,s.subject,o.subject,o.name
```

