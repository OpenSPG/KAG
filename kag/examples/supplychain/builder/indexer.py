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
from kag.builder.component.scanner.csv_scanner import CSVScanner
from kag.examples.supplychain.builder.operator.event_kg_writer_op import EventKGWriter
from kag.examples.supplychain.builder.operator.fund_date_process_op import (
    FundDateProcessComponent,
)
from kag.common.conf import KAG_PROJECT_CONF, KAG_CONFIG
from knext.search.client import SearchClient
from kag.interface import KAGBuilderChain as BuilderChainABC
from knext.search.client import SearchClient
from kag.builder.runner import BuilderChainRunner


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


class SupplyChainCompanyFundTransCompanyChain(BuilderChainABC):
    def __init__(self, spg_type_name: str):
        super().__init__()
        self.spg_type_name = spg_type_name

    def build(self, **kwargs):
        subject_name, relation, object_name = self.spg_type_name.split("_")
        self.date_process_op = FundDateProcessComponent()
        self.mapping = (
            RelationMapping(subject_name, relation, object_name)
            .add_src_id_mapping("srcId")
            .add_dst_id_mapping("dstId")
            .add_sub_property_mapping("transDate", "transDate")
            .add_sub_property_mapping("transAmt", "transAmt")
        )
        self.vectorizer = BatchVectorizer.from_config(
            KAG_CONFIG.all_config["chain_vectorizer"]
        )
        self.sink = KGWriter()
        return self.date_process_op >> self.mapping >> self.vectorizer >> self.sink

    def get_component_with_ckpts(self):
        return [
            self.vectorizer,
        ]


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


class SupplyChainEventBuilderChain(DefaultStructuredBuilderChain):
    def __init__(self, spg_type_name: str, **kwargs):
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
        self.sink = EventKGWriter()
        self.vectorizer = BatchVectorizer.from_config(
            KAG_CONFIG.all_config["chain_vectorizer"]
        )
        chain = self.mapping >> self.vectorizer >> self.sink
        return chain

    def get_component_with_ckpts(self):
        return [
            self.vectorizer,
        ]


def import_data():
    file_path = os.path.dirname(__file__)
    for spg_type_name in [
        "TaxOfCompanyEvent",
        "TaxOfProdEvent",
        "Trend",
        "Industry",
        "Product",
        "Company",
        "Index",
        "Person",
    ]:
        file_name = os.path.join(file_path, f"data/{spg_type_name}.csv")
        if spg_type_name == "Person":
            chain = SupplyChainPersonChain(spg_type_name=spg_type_name)
        else:
            chain = SupplyChainDefaulStructuredBuilderChain(spg_type_name=spg_type_name)
        runner = BuilderChainRunner(
            scanner=CSVScanner(),
            chain=chain,
        )
        runner.invoke(file_name)

    chain = SupplyChainCompanyFundTransCompanyChain(
        spg_type_name="Company_fundTrans_Company"
    )
    runner = BuilderChainRunner(
        scanner=CSVScanner(),
        chain=chain,
    )
    runner.invoke(os.path.join(file_path, "data/Company_fundTrans_Company.csv"))

    chain = SupplyChainEventBuilderChain(spg_type_name="ProductChainEvent")
    runner = BuilderChainRunner(
        scanner=CSVScanner(),
        chain=chain,
    )
    runner.invoke(os.path.join(file_path, "data/ProductChainEvent.csv"))


if __name__ == "__main__":
    import_data()
