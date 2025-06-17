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
from string import Template
from typing import List
from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.interface import PromptABC
from knext.schema.client import SchemaClient


@PromptABC.register("medical_ner")
class OpenIENERPrompt(PromptABC):
    template_zh = """
    {
        "instruction": "你是命名实体识别的专家。请从输入中提取与模式定义匹配的实体。如果不存在该类型的实体，请返回一个空列表。请以JSON字符串格式回应。你可以参照example进行抽取。",
        "schema": $schema,
        "example": [
            {
                "input": "烦躁不安、语妄、失眠酌用镇静药，禁用抑制呼吸的镇静药。\n3.并发症的处理经抗菌药物治疗后，高热常在24小时内消退，或数日内逐渐下降。\n若体温降而复升或3天后仍不降者，应考虑SP的肺外感染。\n治疗：接胸腔压力调节管＋吸引机负压吸引水瓶装置闭式负压吸引宜连续，如经12小时后肺仍未复张，应查找原因。",
                "output": [
                        {"name": "烦躁不安", "category": "Symptom"},
                        {"name": "语妄", "category": "Symptom"},
                        {"name": "失眠", "category": "Symptom"},
                        {"name": "镇静药", "category": "Medicine"},
                        {"name": "肺外感染", "category": "Disease"},
                        {"name": "胸腔压力调节管", "category": "MedicalEquipment"},
                        {"name": "吸引机负压吸引水瓶装置", "category": "MedicalEquipment"},
                        {"name": "闭式负压吸引", "category": "SurgicalOperation"}
                    ]
            }
        ],
        "input": "$input"
    }    
        """

    template_en = template_zh

    def __init__(self, language: str = "", **kwargs):
        super().__init__(language, **kwargs)
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.schema = SchemaClient(
            host_addr=kag_project_config.host_addr,
            project_id=kag_project_config.project_id,
        ).extract_types(kag_project_config.language)
        self.template = Template(self.template).safe_substitute(schema=self.schema)

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        if isinstance(rsp, dict) and "named_entities" in rsp:
            entities = rsp["named_entities"]
        else:
            entities = rsp

        return entities
