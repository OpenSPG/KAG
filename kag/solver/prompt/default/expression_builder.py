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
from json import JSONDecodeError
from typing import List, Optional

from kag.common.base.prompt_op import PromptOp


class ExpressionBuilder(PromptOp):

    template_en = """
{
  "instruction": "你是一个数学专家，请按照给出的问题和数据，输出计算表达式。表达式是Python语法，可以被eval执行。不要包含变量。",
  "example": [
    {
      "input": {
        "question": "Calculate the current rate.",
        "context": {
          "overall_question": "What was gaming revenue in 2020 if it continues to grow at its current rate?",
          "history": [
            {
              "subquery": "Get gaming revenue for 2019, year before 2020.",
              "answer": "1733"
            },
            {
              "subquery": "Get gaming revenue for 2018, year before 2019.",
              "answer": "1912"
            }
          ]
        }
      },
      "output": "1.0*(1733-1912)/1912"
    }
  ],
  "input": "$input"
}
"""

    template_zh = template_en

    def __init__(self, language: Optional[str] = "en", **kwargs):
        super().__init__(language, **kwargs)

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            try:
                rsp = json.loads(rsp)
            except JSONDecodeError as e:
                pass
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        rsp = rsp.strip("`").strip("python").strip("\n")
        return rsp