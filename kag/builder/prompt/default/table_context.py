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
  "task": "表格关键字提取",
  "description": "帮助我从给定的文本中识别出与表格紧密相关的部分，并从中提取有助于理解该表格的关键字或短语。",
  "instruction": [
    "仔细阅读给出的全部文本，包括表格前后的上下文。",
    "定位相关段落: 找出那些直接讨论、解释或者引用了目标表格（即指定要分析的那个表格）的所有句子或段落。",
    "关键字提取: 从上述定位到的相关段落里，挑选出能够最好地描述表格内容、结构或其重要性的词汇和短语作为关键字。这些关键字应该能够帮助读者快速把握表格的核心信息。"
  ],
  "examples": [
    {
      "input": "中芯国际财报2024_3.pdf#7\n2024 年第三季度报告\n本公司董事会及全体董事保证本公告内容不存在任何虚假记载、误导性陈述或者重大遗漏，并对其内容的真实性、准确性和完整性依法承担法律责任。\n2024 年第三季度报告-二、主要财务数据\n2024 年第三季度报告-二、主要财务数据-(一)主要会计数据和财务指标\n单位：千元  币种：人民币\n\n** Target Table **\n### Other Table ###\n### Other Table ###\n附注：\n(1) \"本报告期\"指本季度初至本季度末 3 个月期间，下同。\n(2) 根据 2023 年 12 月 22 日最新公布的《公开发行证券的公司信息披露解释性公告第 1 号—非经常性损益（2023 年修订）》，本公司重述上年同期归属于上市公司股东的扣除非经常性损益的净利润。",
      "output": {
        "table_desc": [
          "2024 年第三季度报告-二、主要财务数据-(一)主要会计数据和财务指标 单位：千元  币种：人民币"
        ],
        "keywords": [
          "中芯国际",
          "2024年第三季度报告",
          "主要财务数据",
          "主要会计数据和财务指标",
          "单位：千元",
          "币种：人民币"
        ]
      }
    }
  ],
  "intput": "$input"
}
"""

    template_en = """
{
  "task": "Table Keyword Extraction",
  "description": "Help me identify sections closely related to a given table from the provided text, and extract keywords or phrases that help in understanding the table.",
  "instruction": [
    "Carefully read the entire provided text, including the context before and after the table.",
    "Locate relevant paragraphs: Identify sentences or paragraphs that directly discuss, explain, or reference the target table (i.e., the specified table to be analyzed).",
    "Keyword extraction: From the located relevant paragraphs, select words and phrases that best describe the table's content, structure, or significance as keywords. These keywords should help readers quickly grasp the core information of the table.",
    "Special note: Avoid extracting any information that appears directly in the table as keywords. Our goal is to supplement and deepen the understanding of the table through surrounding descriptions, rather than repeating the existing data details."
  ],
  "examples": [
    {
      "input": "strategy to provide omni-channel solutions that combine gateway services, payment service provisioning and merchant acquiring across Europe.\nThis transaction was accounted for as a business combination.\nWe recorded the assets acquired, liabilities assumed and noncontrolling interest at their estimated fair values as of the acquisition date.\nIn connection with the acquisition of Realex, we paid a transaction-related tax of $1.2 million.\nOther acquisition costs were not material.\nThe revenue and earnings of Realex for the year ended May 31, 2015 were not material nor were the historical revenue and earnings of Realex material for the purpose of presenting pro forma information for the current or prior-year periods.\nThe estimated acquisition date fair values of the assets acquired, liabilities assumed and the noncontrolling interest, including a reconciliation to the total purchase consideration, are as follows (in thousands):\n## Table 0 ##\nGoodwill of $66.8 million arising from the acquisition, included in the Europe segment, was attributable to expected growth opportunities in Europe, potential synergies from combining our existing business with gateway services and payment service provisioning in certain markets and an assembled workforce to support the newly acquired technology.\nGoodwill associated with this acquisition is not deductible for income tax purposes.\nThe customer-related intangible assets have an estimated amortization period of 16 years.\nThe acquired technology has an estimated amortization period of 10 years.\nThe trade name has an estimated amortization period of 7 years.",
      "output": {
        "table_desc": "The estimated acquisition date fair values of the assets acquired, liabilities assumed and the noncontrolling interest, including a reconciliation to the total purchase consideration, are as follows (in thousands):",
        "keywords": [
          "acquisition date fair values",
          "the acquisition of Realex"
        ]
      }
    }
  ],
  "intput": "$input"
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
        return rsp
