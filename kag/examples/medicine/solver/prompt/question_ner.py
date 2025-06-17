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

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import PromptABC
from knext.schema.client import SchemaClient


@PromptABC.register("example_medical_question_ner")
class QuestionNER(PromptABC):

    template_zh = """
{
    "instruction": "你是命名实体识别的专家。请从输入中提取与模式定义匹配的实体。如果不存在该类型的实体，请返回一个空列表。请以JSON字符串格式回应。你可以参照example进行抽取。",
    "schema": $schema,
    "example": [
        {
            "input": "患儿3岁，因发热呕吐15天住院。查体，嗜睡状。营养差，右侧鼻唇沟变浅，心肺腹部未见异常。脑脊液：蛋白800mg/L，糖2.24mmol/L，氯化物100mmol/L。治疗应是:
A. 青霉素
B. 异烟肼
C. 泼尼松
D. INH+RF
",
            "output": [
                    {"entity": "发热呕吐", "category": "Disease"},
                    {"entity": "嗜睡状", "category": "Symptom"},
                    {"entity": "营养差", "category": "Symptom"},
                    {"entity": "右侧鼻唇沟变浅", "category": "Symptom"},
                    {"entity": "心肺腹部未见异常", "category": "Symptom"},
                    {"entity": "蛋白800mg/L", "category": "ExaminationTest"},
                    {"entity": "糖2.24mmol/L", "category": "ExaminationTest"},
                    {"entity": "氯化物100mmol/L", "category": "ExaminationTest"},
                    {"entity": "青霉素", "category": "Medicine"},
                    {"entity": "异烟肼", "category": "Medicine"},
                    {"entity": "泼尼松", "category": "Medicine"},
                    {"entity": "INH", "category": "Medicine"},
                    {"entity": "RF", "category": "Medicine"}
                ]
        }
    ],
    "input": "$input"
}    
    """

    template_en = template_zh

    def __init__(self, language: str = "en", **kwargs):
        super().__init__(language, **kwargs)
        self.schema = SchemaClient(
            host_addr=KAG_PROJECT_CONF.host_addr, project_id=self.project_id
        ).extract_types(KAG_PROJECT_CONF.language)
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
