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
from typing import List, Optional

from kag.common.base.prompt_op import PromptOp


class TableContextKeyWordsExtractPrompt(PromptOp):
    """
    表格上下文信息提取
    """

    template_zh = """
{
  "task": "关键字提取以及口语化表达",
  "description": "从给出的文本中，提取关键字，并给出口语化的表达方式。",
  "instruction": [
    "一次输入多行文本，每行文本独立处理",
    "先提取关键字，再给出每个关键字多种口语化表达方式。",
    "不可拆分的关键字不需要输出"
  ],
  "examples": [
    {
      "input": {
        "key_list": [
          "('集团公司', '公司高管', '住宿定额')",
          "('集团公司', '平台专业职高级经理、资深专家', '差勤补助定额')",
          "一类",
          ""
        ],
        "context": "key_list属于表【差旅管理办法#1住宿定额、差勤补助定额标准表】中的表头和行头关键字"
      },
      "output": [
        {
          "key": "('集团公司', '公司高管', '住宿定额')",
          "keywords_and_colloquial_expression": {
            "集团公司": [
              "公司"
            ],
            "公司高管": [
              "高管",
              "领导"
            ],
            "住宿定额": [
              "住宿报销",
              "住宿补助"
            ]
          }
        },
        {
          "key": "('集团公司', '平台专业职高级经理、资深专家', '差勤补助定额')",
          "keywords_and_colloquial_expression": {
            "集团公司": [
              "公司"
            ],
            "平台专业职高级经理": [
              "高级经理",
              "平台经理"
            ],
            "资深专家": [
              "专家"
            ],
            "差勤补助定额": [
              "差勤补助"
            ]
          }
        }
      ]
    }
  ],
  "intput": "$input"
}
"""

    template_en = """
{
  "task": "Keyword Extraction and Colloquial Expression",
  "description": "Extract keywords from the given text and provide colloquial expressions for each keyword.",
  "instruction": [
    "Input multiple lines of text, with each line processed independently.",
    "First, extract the keywords, then provide multiple colloquial expressions for each keyword."
  ],
  "examples": [
    {
      "input": {
        "key_list": [
          "('集团公司', '公司高管', '住宿定额')",
          "('集团公司', '平台专业职高级经理、资深专家', '差勤补助定额')"
        ],
        "context": "key_list belongs to the header and row header keywords in the table [Travel Management Measures #1 Accommodation Quota, Attendance Allowance Quota Standard Table]"
      },
      "output": [
        {
          "key": "('集团公司', '公司高管', '住宿定额')",
          "keywords_and_colloquial_expression": {
            "集团公司": [
              "company"
            ],
            "公司高管": [
              "executive",
              "leader"
            ],
            "住宿定额": [
              "accommodation reimbursement",
              "accommodation allowance"
            ]
          }
        },
        {
          "key": "('集团公司', '平台专业职高级经理、资深专家', '差勤补助定额')",
          "keywords_and_colloquial_expression": {
            "集团公司": [
              "company"
            ],
            "平台专业职高级经理": [
              "senior manager",
              "platform manager"
            ],
            "资深专家": [
              "expert"
            ],
            "差勤补助定额": [
              "attendance allowance"
            ]
          }
        }
      ]
    }
  ],
  "input": "$input"
}
"""

    def __init__(self, language: Optional[str] = "en", **kwargs):
        super().__init__(language, **kwargs)

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        rst = {}
        for item in rsp:
            key = item["key"]
            keywords_and_colloquial_expression = item[
                "keywords_and_colloquial_expression"
            ]
            rst[key] = keywords_and_colloquial_expression
        return rst
