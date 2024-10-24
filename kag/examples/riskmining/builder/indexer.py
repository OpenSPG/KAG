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
from kag.builder.component.vectorizer.batch_vectorizer import BatchVectorizer
from kag.builder.default_chain import DefaultStructuredBuilderChain
from kag.common.env import init_kag_config
from kag.builder.component import KGWriter, RelationMapping, SPGTypeMapping
from kag.builder.component.reader.csv_reader import CSVReader
from knext.builder.builder_chain_abc import BuilderChainABC


class RiskMiningEntityChain(BuilderChainABC):
    def __init__(self, spg_type_name: str):
        super().__init__()
        self.spg_type_name = spg_type_name

    def build(self, **kwargs):
        source = CSVReader(output_type="Dict")
        mapping = SPGTypeMapping(spg_type_name=self.spg_type_name)
        vectorizer = BatchVectorizer()
        sink = KGWriter()

        chain = source >> mapping >> vectorizer >> sink
        return chain

class RiskMiningRelationChain(BuilderChainABC):
    def __init__(self, spg_type_name: str):
        super().__init__()
        self.spg_type_name = spg_type_name

    def build(self, **kwargs):
        source = CSVReader(output_type="Dict")
        subject_name, relation, object_name = self.spg_type_name.split("_")
        mapping = (
            RelationMapping(subject_name, relation, object_name)
            .add_src_id_mapping("src")
            .add_dst_id_mapping("dst")
        )
        sink = KGWriter()
        return source >> mapping >> sink


class RiskMiningPersonFundTransPersonChain(RiskMiningRelationChain):
    def __init__(self, spg_type_name: str):
        super().__init__(spg_type_name)

    def build(self, **kwargs):
        source = CSVReader(output_type="Dict")
        subject_name, relation, object_name = self.spg_type_name.split("_")
        mapping = (
            RelationMapping(subject_name, relation, object_name)
            .add_src_id_mapping("src")
            .add_dst_id_mapping("dst")
            .add_sub_property_mapping("transDate", "transDate")
            .add_sub_property_mapping("transAmt", "transAmt")
        )
        sink = KGWriter()
        return source >> mapping >> sink


def import_data():
    init_kag_config("../kag_config.cfg")
    RiskMiningEntityChain(spg_type_name="Cert").invoke("data/Cert.csv")
    RiskMiningEntityChain(spg_type_name="App").invoke("data/App.csv")
    RiskMiningEntityChain(spg_type_name="Company").invoke("data/Company.csv")
    RiskMiningRelationChain(spg_type_name="Company_hasCert_Cert").invoke(
        "data/Company_hasCert_Cert.csv"
    )
    RiskMiningEntityChain(spg_type_name="Device").invoke("data/Device.csv")
    RiskMiningPersonFundTransPersonChain(
        spg_type_name="Person_fundTrans_Person"
    ).invoke("data/Person_fundTrans_Person.csv")
    RiskMiningRelationChain(spg_type_name="Person_hasCert_Cert").invoke(
        "data/Person_hasCert_Cert.csv"
    )
    RiskMiningRelationChain(
        spg_type_name="Person_hasDevice_Device"
    ).invoke("data/Person_hasDevice_Device.csv")
    RiskMiningRelationChain(
        spg_type_name="Person_holdShare_Company"
    ).invoke("data/Person_holdShare_Company.csv")
    RiskMiningEntityChain(spg_type_name="Person").invoke("data/Person.csv")
    RiskMiningEntityChain(spg_type_name="TaxOfRiskApp").invoke("data/TaxOfRiskApp.csv")
    RiskMiningEntityChain(spg_type_name="TaxOfRiskUser").invoke("data/TaxOfRiskUser.csv")


if __name__ == "__main__":
    import_data()
