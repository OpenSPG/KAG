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
from kag.builder.component import KGWriter
from kag.builder.component.scanner.csv_scanner import CSVScanner
from kag.common.conf import KAG_CONFIG
from kag.open_benchmark.AffairQA.builder.affair_batch_vectorizer import (
    AffairBatchVectorizer,
)
from kag.open_benchmark.AffairQA.builder.mapping import AffairTypeMapping

from kag.interface import KAGBuilderChain as BuilderChainABC
from kag.builder.runner import BuilderChainRunner

zh_to_en_mapping = {
    "人物": "Person",
    "公园": "Park",
    "加油站": "GasStation",
    "医疗机构": "MedicalInstitution",
    "协会": "Association",
    "图书馆": "Library",
    "学校": "School",
    "宗教场所": "ReligiousPlace",
    "政府机构": "GovernmentAgency",
    "旅游景点": "TouristAttraction",
    "旅行社": "TravelAgency",
    "自然保护区": "NatureReserve",
    "许可证": "License",
    "行政区": "AdministrativeRegion",
}


class AffairEntityChain(BuilderChainABC):
    def __init__(self, spg_type_name: str):
        super().__init__()
        self.spg_type_name = spg_type_name

    def build(self, **kwargs):
        mapping = AffairTypeMapping(spg_type_name=self.spg_type_name)
        vectorizer = AffairBatchVectorizer.from_config(
            KAG_CONFIG.all_config["chain_vectorizer"]
        )
        sink = KGWriter()

        chain = mapping >> vectorizer >> sink
        return chain


def import_data():
    file_path = os.path.dirname(__file__)
    for spg_type_name in [
        "医疗机构",  # 只重建医疗机构数据
        "人物",
        "公园",
        "加油站",
        "协会",
        "图书馆",
        "学校",
        "宗教场所",
        "政府机构",
        "旅游景点",
        "旅行社",
        "自然保护区",
        "许可证",
        "行政区",
    ]:
        file_name = os.path.join(file_path, f"data/{spg_type_name}.csv")
        chain = AffairEntityChain(spg_type_name=zh_to_en_mapping[spg_type_name])
        runner = BuilderChainRunner(
            scanner=CSVScanner(),
            chain=chain,
        )
        runner.invoke(file_name)


if __name__ == "__main__":
    import_data()
