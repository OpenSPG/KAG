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


@PromptABC.register("medical_std")
class OpenIEEntitystandardizationdPrompt(PromptABC):
    template_zh = """
{
    "instruction": "input字段包含用户提供的上下文。命名实体字段包含从上下文中提取的命名实体，这些可能是含义不明的缩写、别名或俚语。为了消除歧义，请尝试根据上下文和您自己的知识提供这些实体的官方名称。请注意，具有相同含义的实体只能有一个官方名称。请按照提供的示例中的输出字段格式，以单个JSONArray字符串形式回复，无需任何解释。",
    "example": {
        "input": "烦躁不安、语妄、失眠酌用镇静药，禁用抑制呼吸的镇静药。\n3.并发症的处理经抗菌药物治疗后，高热常在24小时内消退，或数日内逐渐下降。\n若体温降而复升或3天后仍不降者，应考虑SP的肺外感染，如腋胸、心包炎或关节炎等。治疗：接胸腔压力调节管＋吸引机负压吸引水瓶装置闭式负压吸引宜连续，如经12小时后肺仍未复张，应查找原因。",
        "named_entities": [
            {"name": "烦躁不安", "category": "Symptom"},
            {"name": "语妄", "category": "Symptom"},
            {"name": "失眠", "category": "Symptom"},
            {"name": "镇静药", "category": "Medicine"},
            {"name": "肺外感染", "category": "Disease"},
            {"name": "胸腔压力调节管", "category": "MedicalEquipment"},
            {"name": "吸引机负压吸引水瓶装置", "category": "MedicalEquipment"},
            {"name": "闭式负压吸引", "category": "SurgicalOperation"}
        ],
        "output": [
            {"name": "烦躁不安", "category": "Symptom", "official_name": "焦虑不安"},
            {"name": "语妄", "category": "Symptom", "official_name": "谵妄"},
            {"name": "失眠", "category": "Symptom", "official_name": "失眠症"},
            {"name": "镇静药", "category": "Medicine", "official_name": "镇静剂"},
            {"name": "肺外感染", "category": "Disease", "official_name": "肺外感染"},
            {"name": "胸腔压力调节管", "category": "MedicalEquipment", "official_name": "胸腔引流管"},
            {"name": "吸引机负压吸引水瓶装置", "category": "MedicalEquipment", "official_name": "负压吸引装置"},
            {"name": "闭式负压吸引", "category": "SurgicalOperation", "official_name": "闭式负压引流"}
        ]
    },
    "input": $input,
    "named_entities": $named_entities,
}    
    """

    template_en = template_zh

    @property
    def template_variables(self) -> List[str]:
        return ["input", "named_entities"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        if isinstance(rsp, dict) and "named_entities" in rsp:
            standardized_entity = rsp["named_entities"]
        else:
            standardized_entity = rsp
        entities_with_offical_name = set()
        merged = []
        entities = kwargs.get("named_entities", [])
        for entity in standardized_entity:
            merged.append(entity)
            entities_with_offical_name.add(entity["name"])
        # in case llm ignores some entities
        for entity in entities:
            if entity["name"] not in entities_with_offical_name:
                entity["official_name"] = entity["name"]
                merged.append(entity)
        return merged
