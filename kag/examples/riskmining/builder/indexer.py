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
from typing import Mapping
from kag.interface import SourceReaderABC, MappingABC, VectorizerABC, SinkWriterABC
from kag.builder.component.vectorizer.batch_vectorizer import BatchVectorizer
from kag.builder.component import KGWriter, RelationMapping, SPGTypeMapping
from kag.builder.component.reader.csv_reader import CSVReader
from knext.builder.builder_chain_abc import BuilderChainABC


# class RiskMiningEntityChain(BuilderChainABC):
#     def __init__(self, spg_type_name: str):
#         super().__init__()
#         self.spg_type_name = spg_type_name

#     def build(self, **kwargs):
#         source = CSVReader(output_type="Dict")
#         mapping = SPGTypeMapping(spg_type_name=self.spg_type_name)
#         vectorizer = BatchVectorizer()
#         sink = KGWriter()

#         chain = source >> mapping >> vectorizer >> sink
#         return chain


class RiskMiningEntityChain(BuilderChainABC):
    def __init__(
        self,
        reader: SourceReaderABC,
        mapping: MappingABC,
        vectorizer: VectorizerABC,
        writer: SinkWriterABC,
    ):
        super().__init__()
        self.reader = reader
        self.mapping = mapping
        self.vectorizer = vectorizer
        self.writer = writer

    def build(self, **kwargs):
        # source = CSVReader(output_type="Dict")
        # mapping = SPGTypeMapping(spg_type_name=self.spg_type_name)
        # vectorizer = BatchVectorizer()
        # sink = KGWriter()

        chain = self.reader >> self.mapping >> self.vectorizer >> self.writer
        return chain

    def set_name(self, spg_type_name: str):
        self.spg_type_name = spg_type_name


# class RiskMiningRelationChain(BuilderChainABC):
#     def __init__(self, spg_type_name: str):
#         super().__init__()
#         self.spg_type_name = spg_type_name

#     def build(self, **kwargs):
#         source = CSVReader(output_type="Dict")
#         subject_name, relation, object_name = self.spg_type_name.split("_")
#         mapping = (
#             RelationMapping(subject_name, relation, object_name)
#             .add_src_id_mapping("src")
#             .add_dst_id_mapping("dst")
#         )
#         sink = KGWriter()
#         return source >> mapping >> sink


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
    file_path = os.path.dirname(__file__)

    entity_file_dict = {
        "Cert": "Cert.csv",
        "App": "App.csv",
        "Company": "Company.csv",
        "Device": "Device.csv",
        "Person": "Person.csv",
        "TaxOfRiskUser": "TaxOfRiskUser.csv",
        "TaxOfRiskApp": "TaxOfRiskApp.csv",
    }
    relation_file_dict = {
        "Company_hasCert_Cert": "Company_hasCert_Cert.csv",
        "Person_fundTrans_Person": "Person_fundTrans_Person.csv",
        "Person_hasDevice_Device": "Person_hasDevice_Device.csv",
        "Person_holdShare_Company": "Person_holdShare_Company.csv",
    }

    # RiskMiningEntityChain(spg_type_name="Cert").invoke(
    #     os.path.join(file_path, "data/Cert.csv")
    # )
    # RiskMiningEntityChain(spg_type_name="App").invoke(
    #     os.path.join(file_path, "data/App.csv")
    # )
    # RiskMiningEntityChain(spg_type_name="Company").invoke(
    #     os.path.join(file_path, "data/Company.csv")
    # )
    # RiskMiningRelationChain(spg_type_name="Company_hasCert_Cert").invoke(
    #     os.path.join(file_path, "data/Company_hasCert_Cert.csv")
    # )
    # RiskMiningEntityChain(spg_type_name="Device").invoke(
    #     os.path.join(file_path, "data/Device.csv")
    # )
    # RiskMiningPersonFundTransPersonChain(
    #     spg_type_name="Person_fundTrans_Person"
    # ).invoke(os.path.join(file_path, "data/Person_fundTrans_Person.csv"))
    # RiskMiningRelationChain(spg_type_name="Person_hasCert_Cert").invoke(
    #     os.path.join(file_path, "data/Person_hasCert_Cert.csv")
    # )
    # RiskMiningRelationChain(spg_type_name="Person_hasDevice_Device").invoke(
    #     os.path.join(file_path, "data/Person_hasDevice_Device.csv")
    # )
    # RiskMiningRelationChain(spg_type_name="Person_holdShare_Company").invoke(
    #     os.path.join(file_path, "data/Person_holdShare_Company.csv")
    # )
    # RiskMiningEntityChain(spg_type_name="Person").invoke(
    #     os.path.join(file_path, "data/Person.csv")
    # )
    # RiskMiningEntityChain(spg_type_name="TaxOfRiskApp").invoke(
    #     os.path.join(file_path, "data/TaxOfRiskApp.csv")
    # )
    # RiskMiningEntityChain(spg_type_name="TaxOfRiskUser").invoke(
    #     os.path.join(file_path, "data/TaxOfRiskUser.csv")
    # )


if __name__ == "__main__":
    import_data()
