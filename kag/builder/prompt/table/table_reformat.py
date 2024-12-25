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
# task

将给定的表格转换为易于程序处理的标准形式，只保留一行表头和一列Index列

# instruction
分析表格和上下文信息，理解表格内容。
将表格的多行表头合并为一行，表头中的内容要完整且易于理解
将多列index列合并为一列，内容要完整易于理解。如果有总分关系，通过两个空格&nbsp;&nbsp;表明该列子项目
参考给出的例子，输出表格的markdown，其他信息不需要保留

# output_format
输出markdown表格

# examples
## input
| | 截至9月30日止六个月 | | |
|---|---|---|---|
| | 2023 | 2024 | |
| | 人民币 | 人民币 | 美元 | %同比变动 |
| | | (以百万计，百分比及每股数据除外) | | |
| 收入 | 458,946 | 479,739 | 68,362 | 5% |
| 经营利润 | 76,074 | 71,235 | 10,151 | (6)%(2) |
| 经营利润率 | 17% | 15% | | |
| 经调整EBITDA(1) | 101,289 | 98,488 | 14,034 | (3)%(3) |
| 经调整EBITDA利润率(1) | 22% | 21% | | |
| 经调整EBITA(1) | 88,216 | 85,596 | 12,197 | (3)%(3) |
| 经调整EBITA利润率(1) | 19% | 18% | | |
| 净利润 | 59,696 | 67,569 | 9,629 | 13%(4) |
| 归属于普通股股东的净利润 | 62,038 | 68,143 | 9,710 | 10%(4) |
| 非公认会计准则净利润(1) | 85,110 | 77,209 | 11,002 | (9)%(4) |
| 摊薄每股收益(5) | 3.01 | 3.50 | 0.50 | 16%(4)(6) |
| 摊薄每股美国存托股收益(5) | 24.08 | 28.00 | 3.99 | 16%(4)(6) |
| 非公认会计准则摊薄每股收益(1)(5) | 4.13 | 3.94 | 0.56 | (5)%(4)(6) |
| 非公认会计准则摊薄每股美国存托股收益(1)(5) | 33.00 | 31.50 | 4.49 | (5)%(4)(6) |

## output
| (以百万计，百分比及每股数据除外) | 2023-截至9月30日止六个月-人民币 | 2024-截至9月30日止六个月-人民币 | 2024-截至9月30日止六个月-美元 | 2024-截至9月30日止六个月-%同比变动 |
|---|---|---|---|---|
| 收入 | 458,946 | 479,739 | 68,362 | 5% |
| &nbsp;&nbsp;经营利润 | 76,074 | 71,235 | 10,151 | (6)%(2) |
| &nbsp;&nbsp;经营利润率 | 17% | 15% | | |
| &nbsp;&nbsp;经调整EBITDA(1) | 101,289 | 98,488 | 14,034 | (3)%(3) |
| &nbsp;&nbsp;经调整EBITDA利润率(1) | 22% | 21% | | |
| &nbsp;&nbsp;经调整EBITA(1) | 88,216 | 85,596 | 12,197 | (3)%(3) |
| &nbsp;&nbsp;经调整EBITA利润率(1) | 19% | 18% | | |
| 净利润 | 59,696 | 67,569 | 9,629 | 13%(4) |
| &nbsp;&nbsp;归属于普通股股东的净利润 | 62,038 | 68,143 | 9,710 | 10%(4) |
| &nbsp;&nbsp;非公认会计准则净利润(1) | 85,110 | 77,209 | 11,002 | (9)%(4) |
||||
| 摊薄每股收益(5) | 3.01 | 3.50 | 0.50 | 16%(4)(6) |
| 摊薄每股美国存托股收益(5) | 24.08 | 28.00 | 3.99 | 16%(4)(6) |
| 非公认会计准则摊薄每股收益(1)(5) | 4.13 | 3.94 | 0.56 | (5)%(4)(6) |
| 非公认会计准则摊薄每股美国存托股收益(1)(5) | 33.00 | 31.50 | 4.49 | (5)%(4)(6) |

# real input
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
        return rsp
