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
from kag.builder.component import KGWriter, RelationMapping, SPGTypeMapping
from kag.builder.component.scanner.csv_scanner import CSVScanner
from kag.common.conf import KAG_CONFIG
from kag.interface import KAGBuilderChain as BuilderChainABC
from kag.builder.runner import BuilderChainRunner

zh_to_en_mapping = {
    "人物": "Person",
    "公园": "Park",
    "加油站": "GasStation",
    "医疗机构": "Hospital",
    "协会": "Association",
    "图书馆": "Library",
    "学校": "School",
    "宗教场所": "ReligiousPlace",
    "政府机构": "GovernmentAgency",
    "旅游景点": "TouristAttraction",
    "旅行社": "TravelAgency",
    "自然保护区": "NatureReserve",
    "许可证": "License",
}


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


def import_data():
    file_path = os.path.dirname(__file__)
    for spg_type_name in [
        "人物",
        "公园",
        "加油站",
        "医疗机构",
        "协会",
        "图书馆",
        "学校",
        "宗教场所",
        "政府机构",
        "旅游景点",
        "旅行社",
        "自然保护区",
        "许可证",
    ]:
        file_name = os.path.join(file_path, f"data/{spg_type_name}.csv")
        chain = RiskMiningEntityChain(spg_type_name=zh_to_en_mapping[spg_type_name])
        runner = BuilderChainRunner(
            scanner=CSVScanner(),
            chain=chain,
        )
        runner.invoke(file_name)


if __name__ == "__main__":
    import_data()
