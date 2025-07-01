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

import json
from typing import List

from kag.interface import PromptABC


@PromptABC.register("medical_triple")
class OpenIETriplePrompt(PromptABC):
    template_zh = """
{
    "instruction": "您是一位专门从事开放信息提取（OpenIE）的专家。请从input字段的文本中提取任何可能的关系（包括主语、谓语、宾语），并按照JSON格式列出它们，须遵循example字段的示例格式。请注意以下要求：1. 每个三元组应至少包含entity_list实体列表中的一个，但最好是两个命名实体。2. 明确地将代词解析为特定名称，以保持清晰度。",
    "entity_list": $entity_list,
    "input": "$input",
    "example": {
        "input": "烦躁不安、语妄、失眠酌用镇静药，禁用抑制呼吸的镇静药。\n3.并发症的处理经抗菌药物治疗后，高热常在24小时内消退，或数日内逐渐下降。\n若体温降而复升或3天后仍不降者，应考虑SP的肺外感染，如腋胸、心包炎或关节炎等。治疗：接胸腔压力调节管＋吸引机负压吸引水瓶装置闭式负压吸引宜连续，如经12小时后肺仍未复张，应查找原因。",
        "entity_list": [
            {"name": "烦躁不安", "category": "Symptom"},
            {"name": "语妄", "category": "Symptom"},
            {"name": "失眠", "category": "Symptom"},
            {"name": "镇静药", "category": "Medicine"},
            {"name": "肺外感染", "category": "Disease"},
            {"name": "胸腔压力调节管", "category": "MedicalEquipment"},
            {"name": "吸引机负压吸引水瓶装置", "category": "MedicalEquipment"},
            {"name": "闭式负压吸引", "category": "SurgicalOperation"}
        ],
        "output":[
            ["烦躁不安", "酌用", "镇静药"],
            ["语妄", "酌用", "镇静药"],
            ["失眠", "酌用", "镇静药"],
            ["镇静药", "禁用", "抑制呼吸的镇静药"],
            ["高热", "消退", "24小时内"],
            ["高热", "下降", "数日内"],
            ["体温", "降而复升或3天后仍不降", "肺外感染"],
            ["肺外感染", "考虑", "腋胸、心包炎或关节炎"],
            ["胸腔压力调节管", "接", "吸引机负压吸引水瓶装置"],
            ["闭式负压吸引", "宜连续", "如经12小时后肺仍未复张"]
        ]
    }
}    
    """

    template_en = template_zh

    @property
    def template_variables(self) -> List[str]:
        return ["entity_list", "input"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        if isinstance(rsp, dict) and "triples" in rsp:
            triples = rsp["triples"]
        else:
            triples = rsp

        standardized_triples = []
        for triple in triples:
            if isinstance(triple, list):
                standardized_triples.append(triple)
            elif isinstance(triple, dict):
                s = triple.get("subject")
                p = triple.get("predicate")
                o = triple.get("object")
                if s and p and o:
                    standardized_triples.append([s, p, o])

        return standardized_triples
