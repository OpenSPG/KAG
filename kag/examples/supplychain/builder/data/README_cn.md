# 业务数据介绍

## 1. 数据目录

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

分别抽样部分数据进行介绍。

## 2. 公司数据（Company.csv）

```text
id,name,products
CSF0000002238,三角*胎股*限公司,"轮胎,全钢子午线轮胎"
```

* ``id``：公司在系统中的唯一 id
* ``name``：公司名
* ``products``：公司生产的产品，使用逗号分隔

## 3. 公司资金转账（Company_fundTrans_Company.csv）

```text
src,dst,transDate,transAmt
CSF0000002227,CSF0000001579,20230506,73
```

* ``src``：转出方
* ``dst``：转入方
* ``transDate``：转账日期
* ``transAmt``：转账总金额

