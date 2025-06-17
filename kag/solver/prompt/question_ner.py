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
from knext.reasoner.client import ReasonerClient


@PromptABC.register("default_question_ner")
class QuestionNER(PromptABC):

    template_en = """
    {
        "instruction": "You are an expert in named entity recognition. Please extract entities and that match the schema definition from the input. Please respond in the format of a JSON string.You can refer to the example for extraction.",
        "schema": $schema,
        "output_format": "only output with json format, don't output other information",
        "example": [
            {
                "input": "Which magazine was started first, Arthur's Magazine or First for Women?",
                "output": [
                        {
                            "name": "First for Women",
                            "category": "Works"
                        },
                        {
                            "name": "Arthur's Magazine",
                            "category": "Works"
                        }
                    ]
            }
        ],
        "input": "$input"
    }    
        """

    template_zh = template_en

    def __init__(self, language: str = "", **kwargs):
        super().__init__(language, **kwargs)
        self.schema = (
            ReasonerClient(
                project_id=self.kag_project_config.project_id,
                host_addr=self.kag_project_config.host_addr,
                namespace=self.kag_project_config.namespace,
            )
            .get_reason_schema()
            .keys()
        )
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
