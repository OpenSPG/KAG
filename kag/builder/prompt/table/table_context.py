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

import logging
import json
from typing import List, Optional

from kag.common.base.prompt_op import PromptOp


class TableContextKeyWordsExtractPrompt(PromptOp):
    """
    表格上下文信息提取
    """

    template_zh = """
{
  "task": "提取表格相关的关键字",
  "instruction": [
    "仔细阅读给出的全部文本，包括表格前后的上下文。",
    "定位相关段落: 找出那些直接讨论、解释或者引用了表格的所有句子或段落。",
    "挑选出能够最好地描述表格内容、结构或其重要性的词汇和短语作为关键字。不要出现表头和index列已有的词语。"
    "表格命名：给该表格取一个易于理解的表名"
  ],
  "output_format": "输出json格式，包含table_desc,keywords,table_name",
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
          "主要会计数据和财务指标"
        ],
        "table_name": "中芯国际2024年第三季度主要财务数据"
      }
    }
  ],
  "intput": "$input"
}
"""

    template_en = template_zh

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
            except json.decoder.JSONDecodeError:
                index = rsp.rfind("}")
                rsp = rsp[0:index]
                try:
                    rsp = json.loads(rsp)
                except json.decoder.JSONDecodeError:
                    logging.exception("json_str=%s", rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        return rsp
