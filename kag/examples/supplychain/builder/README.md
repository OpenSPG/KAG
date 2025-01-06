# Enterprise Supply Chain Case Knowledge Graph Construction

[English](./README.md) |
[简体中文](./README_cn.md)

In this example, all the data are structured. There are two main capabilities required in to import the data:

* Structured Mapping: The original data and the schema-defined fields are not completely consistent, so a data field mapping process needs to be defined.

* Entity Linking: In relationship building, entity linking is a very important construction method. This example demonstrates a simple case of implementing entity linking capability for companies.

## 1. Structured Mapping from Source Data to SPG Data

Taking the import of ``Company`` instances as an example:

```text
id,name,products
CSF0000000254,北大*药*份限公司,"医疗器械批发,医药批发,制药,其他化学药品"
```

The code for importing ``Company`` instances is as follows:

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

In general, this mapping relationship can satisfy the import of structured data. However, in some scenarios, it may be necessary to manipulate the data to meet specific requirements. In such cases, we need to implemented a user-defined operator.

## 2. User-defined Entity Linking Operator

Consider the following data:

```text
id,name,age,legalRep
0,路**,63,"新疆*花*股*限公司,三角*胎股*限公司,传化*联*份限公司"
```

The ``legalRep`` field is the company name, but the company ID is set as the primary key, it is not possible to directly associate the company name with a specific company. Assuming there is a search service available that can convert the company name to an ID, a user-defined linking operator needs to be developed to perform this conversion.

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

