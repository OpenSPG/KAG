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
  "instruction": [
    "识别子问题中的关键字，同时给出关键字的多种常见别名"
  ],
  "example": [
    {
      "input": "查找阿里巴巴各部分收入",
      "output": [
        {
          "entity": "阿里巴巴",
          "category": "Keyword",
          "alias": [
            "阿里巴巴集团"
            "阿里集团",
            "阿里",
          ]
        },
        {
          "entity": "收入",
          "category": "Keyword",
          "alias": [
            "营业收入",
            "营收"
          ]
        }
      ]
    }
  ],
  "input": "$input"
}
"""

    template_zh = template_en

    def __init__(self, language: Optional[str] = "en", **kwargs):
        super().__init__(language, **kwargs)
        # self.template = Template(self.template)

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        return rsp
