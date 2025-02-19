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


@PromptABC.register("table_classify")
class TableClassifyPrompt(PromptABC):
    """
    extract table context
    """

    template_zh = """
# Task
针对给出的表格上下文，总结输出表格名称，表格描述信息，表格关键字，最后为表格分类。

# Requirements
表格名称要求易于理解，具有代表性。

## 表格分类
将表格分为两类，矩阵型表格和其他类型表格。

### 矩阵型表格
表格中的数据，需要结合表格行和列索引才能理解。例如财务报表。
例子:
```
主营业务收入分析
| 以地区分类 | 2024 年第三季度（7-9 月） | 2024 年第二季度（4-6 月） | 2023 年第三季度（7-9 月） |
| :--------: | :-----------------------: | :-----------------------: | :-----------------------: |
|   中国区   |          86.4%            |          80.3%            |          84.0%            |
|   美国区   |          10.6%            |          16.0%            |          12.9%            |
|   欧洲区   |          3.0%             |          3.7%             |          3.1%             |
```

# 输出格式
json格式，例子:
```json
{
  "table_desc": "2024第二，三季度以及2023第三季度，中国区，美国区以及欧洲区主营业务收入占比分析",
  "keywords": [
    "主营业务收入"
  ],
  "table_name": "主营业务按照地区分类表",
  "table_type": "矩阵型表格"
}
```

# 输入的表格及其上下文信息
$input
"""

    template_en = """
# Task
Based on the given table context, summarize and output the table name, table description, table keywords, and finally the table classification.

# Requirements
The table name should be easy to understand and representative.

## Table Classification
Classify the table into two categories: MatrixTable and OtherTable.

### MatrixTable
The data in the table requires both row and column indices for comprehension, such as financial statements.
Example:
Revenue Analysis from Main Businesses

| By Region  | Q3 2024 (July-September) | Q2 2024 (April-June) | Q3 2023 (July-September) |
| :--------: | :-----------------------: | :-------------------: | :----------------------: |
|   China    |          86.4%            |         80.3%         |         84.0%            |
|    USA     |          10.6%            |         16.0%         |         12.9%            |
|   Europe   |          3.0%             |         3.7%          |         3.1%             |

# Output Format
JSON format, example:

```json
{
  "table_desc": "Analysis of the revenue share from main businesses in China, USA, and Europe for Q2 and Q3 of 2024 and Q3 of 2023",
  "keywords": [
    "Main Business Revenue"
  ],
  "table_name": "Revenue Share by Region Table",
  "table_type": "MatrixTable"
}
```

# Input Table and Its Context Information
$input
"""

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
