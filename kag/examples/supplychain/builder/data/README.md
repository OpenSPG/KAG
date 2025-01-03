# Introduction to the business data

## 1. Contents of the data directory

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

## 2. Company data（Company.csv）

```text
id,name,products
CSF0000002238,三角*胎股*限公司,"轮胎,全钢子午线轮胎"
```

* ``id``: The unique id in the system of the company
* ``name``: Name of the company
* ``products``: Products produced by the company, separated by commas

## 3. Fund transferring between companies（Company_fundTrans_Company.csv）

```text
src,dst,transDate,transAmt
CSF0000002227,CSF0000001579,20230506,73
```

* ``src``: Funds transferor
* ``dst``: Funds transferee
* ``transDate``: date the fund transferring happens
* ``transAmt``: the amount of transferred fund

