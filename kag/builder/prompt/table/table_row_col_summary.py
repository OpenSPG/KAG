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


@PromptABC.register("table_row_col_summary")
class TableRowColSummaryPrompt(PromptABC):
    """
    矩阵型表格索引信息提取
    """

    template_zh = """
# 你的任务
根据给出的表格和上下文信息，输出表格行和列的摘要信息。
# 操作指南
1. 对表格的每一行，标有row_index_<number>，先判断该行数据属于表头还是数据行，然后总结这一行数据的摘要。
2. 对表格中标有[column_index_<number>]的列，判断该列数据属于索引列还是数据列，然后总结这一列数据的摘要。
3. 摘要不允许重复行或者列中的内容和数据。
4. 确保读者通过摘要，可以完全理解行列数据的信息。
# 输出格式
json格式，例子:
```json
{
  "rows": [
    {"index":0, "type": "header": "summary": "表头摘要"},
    {"index":1, "type": "header": "summary": "多层表头，第二行表头摘要"},
    {"index":3, "type": "data": "summary": "第一行数据摘要"},
  ],
  "columns": [
    {"index":0, "type": "index": "summary": "索引列摘要"},
    {"index":1, "type": "index": "summary": "双索引列，第二列摘要"},
    {"index":2, "type": "data": "summary": "第一列数据摘要"},
  ]
}
```
# 输入表格
$input
# 你的json输出
""".strip()

    template_en = """
# Your Task
Based on the provided table and contextual information, generate a summary for each row and column of the table.
# Instructions
1. For each row in the table, first determine whether the row belongs to the header or the data rows, then summarize the content of that row.
2. For each column in the table, determine whether the column serves as an index column or a data column, then summarize the content of that column.
3. The summaries must not repeat the exact content or data from the rows or columns.
4. Ensure that readers can fully understand the information conveyed by the rows and columns through the summaries alone.
# Output Format
JSON format example:
```json
{
  "rows": [
    {"index":0, "type": "header", "summary": "Summary of the header row"},
    {"index":1, "type": "header", "summary": "Summary of the second header row (multi-level header)"},
    {"index":3, "type": "data", "summary": "Summary of the first data row"}
  ],
  "columns": [
    {"index":0, "type": "index", "summary": "Summary of the index column"},
    {"index":1, "type": "index", "summary": "Summary of the second index column (multi-index structure)"},
    {"index":2, "type": "data", "summary": "Summary of the first data column"}
  ]
}
```
# Input Table
$input
# Your JSON Output
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
