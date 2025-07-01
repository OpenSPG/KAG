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


@PromptABC.register("table_context")
class TableContextPrompt(PromptABC):
    """
    extract table context
    """

    template_zh = """
# Your Task
针对给出的表格及其上下文，总结输出表格名称，表格描述信息，以及表格关键字。
# Requirements
表格名称要求易于理解，信息完整。
# 输出格式
json格式，例子:
```json
{
  "table_desc": "针对表格内容的描述信息",
  "keywords": [
    "关键字列表"
  ],
  "table_name": "表格名称"
}
```
# 表格及其上下文信息
$input
# Your Answer
""".strip()

    template_en = """
# Your Task
Based on the provided table and its context, summarize the table name, table description, and table keywords.
# Requirements
The table name should be easy to understand and provide complete information.
# Output Format
In JSON format, for example:
```json
{
  "table_desc": "Description of the table content",
  "keywords": [
    "List of keywords"
  ],
  "table_name": "Table name"
}
```
# Table and it's Context Information
$input
# Your Answer
""".strip()

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
