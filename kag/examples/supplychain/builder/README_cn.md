# 产业链案例知识构建

[English](./README.md) |
[简体中文](./README_cn.md)

本例中数据均为结构化数据，导入数据主要需要两个能力：

* 结构化 mapping：原始数据和 schema 定义表字段并不完全一致，需要定义数据字段映射过程。

* 实体链指：在关系构建中，实体链指是非常重要的建设手段，本例演示一个简单 case，实现公司的链指能力。

本例中的代码可在 [kag/examples/supplychain/builder/indexer.py](./indexer.py) 中查看。

## 1. 源数据到 SPG 数据的 mapping 能力

以导入 Company 数据为例：

```text
id,name,products
CSF0000000254,北大*药*份限公司,"医疗器械批发,医药批发,制药,其他化学药品"
```

导入 Company 的代码如下：

```python
class SupplyChainDefaulStructuredBuilderChain(BuilderChainABC):
    def __init__(self, spg_type_name: str):
        super().__init__()
        self.spg_type_name = spg_type_name

    def build(self, **kwargs):
        """
        Builds the processing chain for the SPG.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            chain: The constructed processing chain.
        """
        self.mapping = SPGTypeMapping(spg_type_name=self.spg_type_name)
        self.sink = KGWriter()
        self.vectorizer = BatchVectorizer.from_config(
            KAG_CONFIG.all_config["chain_vectorizer"]
        )
        chain = self.mapping >> self.vectorizer >> self.sink
        return chain

    def get_component_with_ckpts(self):
        return [
            self.vectorizer,
        ]
```

一般情况下这种映射关系基本能够满足结构化数据导入，但在一些场景下可能需要对数据进行部分数据才能满足要求，此时就需要实现自定义算子来处理问题。

## 2. 自定义算子实现链指能力

假设有如下数据：

```text
id,name,age,legalRep
0,路**,63,"新疆*花*股*限公司,三角*胎股*限公司,传化*联*份限公司"
```

``legalRep`` 字段为公司名字，但在系统中已经将公司 ``id`` 设置成为主键，直接通过公司名是无法关联到具体公司，假定存在一个搜索服务，可将公司名转换为 ``id``，此时需要自定开发一个链指算子，实现该过程的转换:

```python
def company_link_func(prop_value, node):
    sc = SearchClient(KAG_PROJECT_CONF.host_addr, KAG_PROJECT_CONF.project_id)
    company_id = []
    records = sc.search_text(
        prop_value, label_constraints=["SupplyChain.Company"], topk=1
    )
    if records:
        company_id.append(records[0]["node"]["id"])
    return company_id


class SupplyChainPersonChain(BuilderChainABC):
    def __init__(self, spg_type_name: str):
        # super().__init__()
        self.spg_type_name = spg_type_name

    def build(self, **kwargs):
        self.mapping = (
            SPGTypeMapping(spg_type_name=self.spg_type_name)
            .add_property_mapping("name", "name")
            .add_property_mapping("id", "id")
            .add_property_mapping("age", "age")
            .add_property_mapping(
                "legalRepresentative",
                "legalRepresentative",
                link_func=company_link_func,
            )
        )
        self.vectorizer = BatchVectorizer.from_config(
            KAG_CONFIG.all_config["chain_vectorizer"]
        )
        self.sink = KGWriter()
        return self.mapping >> self.vectorizer >> self.sink

    def get_component_with_ckpts(self):
        return [
            self.vectorizer,
        ]

    def close_checkpointers(self):
        for node in self.get_component_with_ckpts():
            if node and hasattr(node, "checkpointer"):
                node.checkpointer.close()
```

