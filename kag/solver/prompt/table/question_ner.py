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
from typing import List, Optional

from kag.common.base.prompt_op import PromptOp
from knext.reasoner.client import ReasonerClient


class QuestionNER(PromptOp):

    template_en = """
    {
        "instruction": "You are an expert in named entity recognition. Please extract entities and keywords. Please respond in the format of a JSON string. You can refer to the example for extraction.",
        "schema": $schema,
        "example": [
            {
                "input": "Which year is Total Revenues of Group retirement products the most?",
                "output": [
                        {
                            "entity": "Total Revenues",
                            "category": "Keyword"
                        },
                        {
                            "entity": "Group retirement products",
                            "category": "Keyword"
                        }
                    ]
            }
        ],
        "input": "$input"
    }    
        """

    template_zh = template_en

    def __init__(
            self, language: Optional[str] = "en", **kwargs
    ):
        super().__init__(language, **kwargs)
        #self.template = Template(self.template)

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
