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

from kag.interface import PromptABC


@PromptABC.register("matrix_table_index")
class MatrixTableIndexPrompt(PromptABC):
    """
    矩阵型表格索引信息提取
    """

    template_zh = """
# Task
总结矩阵型表格行头和列头表达的完整信息，使得表格中每个数据结合行头和列头就能理解其意义。

# Instruction
1. 对表格的每一行，输出该行头所表达的信息。
2. 对表格的每一列，输出这一列头表达的信息。

# 输出格式
json格式，例子:
```json
{
  "rows": [
    "X公司营业收入",
    "X公司利润",
  ],
  "columns": [
    "2013年全年美元计价",
    "2012年四季度同比增长百分比"
  ]
}
```
# 输入表格
$input
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
            except json.decoder.JSONDecodeError as e:
                  logging.exception("json_str=%s", rsp)
                  raise e
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        return rsp
