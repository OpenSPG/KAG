# Introduction to Data of Enterprise Supply Chain

[English](./README.md) |
[简体中文](./README_cn.md)

## 1. Directory Structure

```text
supplychain
├── builder
│   ├── data
│   │   ├── Company.csv
│   │   ├── CompanyUpdate.csv
│   │   ├── Company_fundTrans_Company.csv
│   │   ├── Index.csv
│   │   ├── Industry.csv
│   │   ├── Person.csv
│   │   ├── Product.csv
│   │   ├── ProductChainEvent.csv
│   │   ├── TaxOfCompanyEvent.csv
│   │   ├── TaxOfProdEvent.csv
│   │   └── Trend.csv
```

We will introduce the tables by sampling some rows from each one.

## 2. The company instances (Company.csv)

```text
id,name,products
CSF0000002238,三角*胎股*限公司,"轮胎,全钢子午线轮胎"
```

* ``id``: The unique id of the company
* ``name``: Name of the company
* ``products``: Products produced by the company, separated by commas

## 3. Fund transferring between companies (Company_fundTrans_Company.csv)

```text
src,dst,transDate,transAmt
CSF0000002227,CSF0000001579,20230506,73
```

* ``src``: The source of the fund transfer
* ``dst``: The destination of the fund transfer
* ``transDate``: The date of the fund transfer
* ``transAmt``: The total amount of the fund transfer

## 4. The Person instances (Person.csv)

```text
id,name,age,legalRep
0,路**,63,"新疆*花*股*限公司,三角*胎股*限公司,传化*联*份限公司"
```

* ``id``: The unique id of the person
* ``name``: Name of the person
* ``age``: Age of the person
* ``legalRep``: Company list with the person as the legal representative, separated by commas

## 5. The industry concepts (Industry.csv)

```text
fullname
能源
能源-能源
能源-能源-能源设备与服务
能源-能源-能源设备与服务-能源设备与服务
能源-能源-石油、天然气与消费用燃料
```

The industry chain concepts is represented by its name, with dashes indicating its higher-level concepts.
For example, the higher-level concept of "能源-能源-能源设备与服务" is "能源-能源",
and the higher-level concept of "能源-能源-能源设备与服务-能源设备与服务" is "能源-能源-能源设备与服务".

## 6. The product concepts (Product.csv)

```text
fullname,belongToIndustry,hasSupplyChain
商品化工-橡胶-合成橡胶-顺丁橡胶,原材料-原材料-化学制品-商品化工,"化工商品贸易-化工产品贸易-橡塑制品贸易,轮胎与橡胶-轮胎,轮胎与橡胶-轮胎-特种轮胎,轮胎与橡胶-轮胎-工程轮胎,轮胎与橡胶-轮胎-斜交轮胎,轮胎与橡胶-轮胎-全钢子午线轮胎,轮胎与橡胶-轮胎-半钢子午线轮胎"
```

* ``fullname``: The name of the product, with dashes indicating its higher-level concepts.
* ``belongToIndustry``: The industry which the product belongs to. For example, in this case, "顺丁橡胶" belongs to "商品化工".
* ``hasSupplyChain``: The downstream industries related to the product, separated by commas. For example, the downstream industries of "顺丁橡胶" may include "橡塑制品贸易", "轮胎", and so on.

## 7. The industry chain events (ProductChainEvent.csv)

```text
id,name,subject,index,trend
1,顺丁橡胶成本上涨,商品化工-橡胶-合成橡胶-顺丁橡胶,价格,上涨
```

* ``id``: The ID of the event
* ``name``: The name of the event
* ``subject``: The subject of the event. In this example, it is "顺丁橡胶".
* ``index``: The index related to the event. In this example, it is "价格" (price).
* ``trend``: The trend of the event. In this example, it is "上涨" (rising).

## 8. The index concepts (Index.csv) and the trend concepts (Trend.csv)

Index and trend are atomic conceptual categories that can be combined to form industrial chain events and company events.

* index: The index related to the event, with possible values of "价格" (price), "成本" (cost) or "利润" (profit).
* trend: The trend of the event, with possible values of "上涨" (rising) or "下跌" (falling).

## 9 The event categorization (TaxOfProdEvent.csv, TaxOfCompanyEvent.csv)

Event classification includes industrial chain event classification and company event classification with the following data:

* Industrial chain event classification: "价格上涨" (price rising).
* Company event classification: "成本上涨" (cost rising), "利润下跌" (profit falling).

