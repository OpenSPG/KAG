# -*- coding: utf-8 -*-
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.
import os

from kag.builder.component.vectorizer.batch_vectorizer import BatchVectorizer
from kag.builder.default_chain import DefaultStructuredBuilderChain
from kag.builder.component import SPGTypeMapping, KGWriter, RelationMapping
from kag.builder.component.reader.csv_reader import CSVReader
from kag.examples.supplychain.builder.operator.event_kg_writer_op import EventKGWriter
from kag.examples.supplychain.builder.operator.fund_date_process_op import (
    FundDateProcessComponent,
)
from kag.common.conf import KAG_PROJECT_CONF, KAG_CONFIG
from knext.search.client import SearchClient
from kag.interface import KAGBuilderChain as BuilderChainABC
from knext.search.client import SearchClient


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
        super().__init__()
        self.spg_type_name = spg_type_name

    def build(self, **kwargs):
        source = CSVReader(output_type="Dict")
        mapping = (
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
        vectorizer = BatchVectorizer.from_config(KAG_CONFIG.all_config["vectorizer"])
        sink = KGWriter()
        return source >> mapping >> vectorizer >> sink


class SupplyChainCompanyFundTransCompanyChain(BuilderChainABC):
    def __init__(self, spg_type_name: str):
        super().__init__()
        self.spg_type_name = spg_type_name

    def build(self, **kwargs):
        source = CSVReader(output_type="Dict")
        subject_name, relation, object_name = self.spg_type_name.split("_")
        date_process_op = FundDateProcessComponent()
        mapping = (
            RelationMapping(subject_name, relation, object_name)
            .add_src_id_mapping("srcId")
            .add_dst_id_mapping("dstId")
            .add_sub_property_mapping("transDate", "transDate")
            .add_sub_property_mapping("transAmt", "transAmt")
        )
        vectorizer = BatchVectorizer.from_config(KAG_CONFIG.all_config["vectorizer"])
        sink = KGWriter()
        return source >> date_process_op >> mapping >> vectorizer >> sink


class SupplyChainDefaulStructuredBuilderChain(DefaultStructuredBuilderChain):
    def __init__(self, spg_type_name: str, **kwargs):
        super().__init__(spg_type_name, **kwargs)

    def build(self, **kwargs):
        """
        Builds the processing chain for the SPG.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            chain: The constructed processing chain.
        """
        source = CSVReader(output_type="Dict")
        mapping = SPGTypeMapping(spg_type_name=self.spg_type_name)
        sink = KGWriter()
        vectorizer = BatchVectorizer.from_config(KAG_CONFIG.all_config["vectorizer"])
        chain = source >> mapping >> vectorizer >> sink
        return chain


class SupplyChainEventBuilderChain(DefaultStructuredBuilderChain):
    def __init__(self, spg_type_name: str, **kwargs):
        super().__init__(spg_type_name, **kwargs)

    def build(self, **kwargs):
        """
        Builds the processing chain for the SPG.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            chain: The constructed processing chain.
        """
        source = CSVReader(output_type="Dict")
        mapping = SPGTypeMapping(spg_type_name=self.spg_type_name)
        sink = EventKGWriter()
        vectorizer = BatchVectorizer.from_config(KAG_CONFIG.all_config["vectorizer"])
        chain = source >> mapping >> vectorizer >> sink
        return chain


def import_data():
    file_path = os.path.dirname(__file__)
    SupplyChainDefaulStructuredBuilderChain(spg_type_name="TaxOfCompanyEvent").invoke(
        file_path=os.path.join(file_path, "data/TaxOfCompanyEvent.csv")
    )
    SupplyChainDefaulStructuredBuilderChain(spg_type_name="TaxOfProdEvent").invoke(
        file_path=os.path.join(file_path, "data/TaxOfProdEvent.csv")
    )
    SupplyChainDefaulStructuredBuilderChain(spg_type_name="Trend").invoke(
        file_path=os.path.join(file_path, "data/Trend.csv")
    )
    SupplyChainDefaulStructuredBuilderChain(spg_type_name="Industry").invoke(
        file_path=os.path.join(file_path, "data/Industry.csv")
    )
    SupplyChainDefaulStructuredBuilderChain(spg_type_name="Product").invoke(
        file_path=os.path.join(file_path, "data/Product.csv")
    )
    SupplyChainDefaulStructuredBuilderChain(spg_type_name="Company").invoke(
        file_path=os.path.join(file_path, "data/Company.csv")
    )
    SupplyChainDefaulStructuredBuilderChain(spg_type_name="Index").invoke(
        file_path=os.path.join(file_path, "data/Index.csv")
    )
    SupplyChainPersonChain(spg_type_name="Person").invoke(
        file_path=os.path.join(file_path, "data/Person.csv")
    )

    SupplyChainCompanyFundTransCompanyChain(
        spg_type_name="Company_fundTrans_Company"
    ).invoke(file_path=os.path.join(file_path, "data/Company_fundTrans_Company.csv"))
    SupplyChainEventBuilderChain(spg_type_name="ProductChainEvent").invoke(
        file_path=os.path.join(file_path, "data/ProductChainEvent.csv")
    )


if __name__ == "__main__":
    import_data()
