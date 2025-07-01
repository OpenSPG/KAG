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
from kag.builder.component import KGWriter, RelationMapping, SPGTypeMapping
from kag.builder.component.scanner.csv_scanner import CSVScanner
from kag.common.conf import KAG_CONFIG
from kag.interface import KAGBuilderChain as BuilderChainABC
from kag.builder.runner import BuilderChainRunner


class RiskMiningEntityChain(BuilderChainABC):
    def __init__(self, spg_type_name: str):
        super().__init__()
        self.spg_type_name = spg_type_name

    def build(self, **kwargs):
        mapping = SPGTypeMapping(spg_type_name=self.spg_type_name)
        vectorizer = BatchVectorizer.from_config(
            KAG_CONFIG.all_config["chain_vectorizer"]
        )
        sink = KGWriter()

        chain = mapping >> vectorizer >> sink
        return chain


class RiskMiningRelationChain(BuilderChainABC):
    def __init__(self, spg_type_name: str):
        super().__init__()
        self.spg_type_name = spg_type_name

    def build(self, **kwargs):
        subject_name, relation, object_name = self.spg_type_name.split("_")
        mapping = (
            RelationMapping(subject_name, relation, object_name)
            .add_src_id_mapping("src")
            .add_dst_id_mapping("dst")
        )
        sink = KGWriter()
        return mapping >> sink


class RiskMiningPersonFundTransPersonChain(RiskMiningRelationChain):
    def __init__(self, spg_type_name: str):
        super().__init__(spg_type_name)

    def build(self, **kwargs):
        subject_name, relation, object_name = self.spg_type_name.split("_")
        mapping = (
            RelationMapping(subject_name, relation, object_name)
            .add_src_id_mapping("src")
            .add_dst_id_mapping("dst")
            .add_sub_property_mapping("transDate", "transDate")
            .add_sub_property_mapping("transAmt", "transAmt")
        )
        sink = KGWriter()
        return mapping >> sink


def import_data():
    file_path = os.path.dirname(__file__)
    for spg_type_name in [
        "App",
        "Cert",
        "Company",
        "Device",
        "Person",
        "TaxOfRiskApp",
        "TaxOfRiskUser",
    ]:
        file_name = os.path.join(file_path, f"data/{spg_type_name}.csv")
        chain = RiskMiningEntityChain(spg_type_name=spg_type_name)
        runner = BuilderChainRunner(
            scanner=CSVScanner(),
            chain=chain,
        )
        runner.invoke(file_name)

    for spg_type_name in [
        "Company_hasCert_Cert",
        "Person_fundTrans_Person",
        "Person_hasCert_Cert",
        "Person_hasDevice_Device",
        "Person_holdShare_Company",
    ]:
        file_name = os.path.join(file_path, f"data/{spg_type_name}.csv")
        if spg_type_name == "Person_fundTrans_Person":
            chain = RiskMiningPersonFundTransPersonChain(spg_type_name=spg_type_name)
        else:
            chain = RiskMiningRelationChain(spg_type_name=spg_type_name)
        runner = BuilderChainRunner(
            scanner=CSVScanner(),
            chain=chain,
        )
        runner.invoke(file_name)


if __name__ == "__main__":
    import_data()
