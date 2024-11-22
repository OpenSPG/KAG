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
        return mapping >> vectorizer >> sink


class SupplyChainCompanyFundTransCompanyChain(BuilderChainABC):
    def __init__(self, spg_type_name: str):
        super().__init__()
        self.spg_type_name = spg_type_name

    def build(self, **kwargs):
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
        return date_process_op >> mapping >> vectorizer >> sink


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
        mapping = SPGTypeMapping(spg_type_name=self.spg_type_name)
        sink = KGWriter()
        vectorizer = BatchVectorizer.from_config(KAG_CONFIG.all_config["vectorizer"])
        chain = mapping >> vectorizer >> sink
        return chain


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

        mapping = SPGTypeMapping(spg_type_name=self.spg_type_name)
        sink = EventKGWriter()
        vectorizer = BatchVectorizer.from_config(KAG_CONFIG.all_config["vectorizer"])
        chain = mapping >> vectorizer >> sink
        return chain


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
            num_parallel=4,
            reader=CSVReader(),
            chain=chain,
        )
        runner.invoke(file_name)

    chain = SupplyChainCompanyFundTransCompanyChain(
        spg_type_name="Company_fundTrans_Company"
    )
    runner = BuilderChainRunner(
        reader=CSVReader(),
        chain=chain,
    )
    runner.invoke(os.path.join(file_path, "data/Company_fundTrans_Company.csv"))

    chain = SupplyChainEventBuilderChain(spg_type_name="ProductChainEvent")
    runner = BuilderChainRunner(
        reader=CSVReader(),
        chain=chain,
    )
    runner.invoke(os.path.join(file_path, "data/ProductChainEvent.csv"))


if __name__ == "__main__":
    import_data()
