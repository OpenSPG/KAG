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


class TableClassifyPrompt(PromptOp):
    """
    表格分类prompt和结果解析
    """

    template_zh = """
{
  "task": "表格分类与信息提取",
  "description": "本任务旨在将给定的表格分为三类：指标型表格、简单表格和其他表格。对于每种类型的表格，需要提取并输出特定的信息。",
  "categories": [
    {
      "name": "指标型表格",
      "definition": "核心内容是数值的表格，如财务报表等。",
      "required_output": {
        "header": "表头占据的行索引（从0开始计数）",
        "index_col": "列关键标识符所在的列索引（从0开始计数）",
        "units": "度量单位，例如美元或人民币",
        "scale": "数值尺度，例如千、百万"
      },
      "examples": [
        {
          "input": "下面是各个成员国关税收入统计:\n| (in millions) | 收入       |      收入 |\n| ------------- | ---------- | ---------:|\n|               | 2019       |     2018  |\n| 亚洲          | 21,614     |   20,156  |\n| 　中国        | 16,883     |   14,465  |\n| 　印度        | 4,731      |    5,691  |\n| 澳洲          | 2,341      |    2,231  |\n| 总计          | 23,955     |   22,387  |",
          "output": {
            "table_type": "指标型表格",
            "header": [
              0,
              1
            ],
            "index_col": [
              0
            ],
            "units": "美元",
            "scale": "millions"
          }
        },
        {
          "input": "国内出差住宿定额、差勤补助定额标准表\n| 公司     | 人员分类                     | 项  目       | 各地区标准   | 各地区标准   | 各地区标准   |\n|----------|------------------------------|--------------|--------------|--------------|--------------|\n| 公司     | 人员分类                     | 项  目       | 一类         | 二类         | 三类         |\n| 集团公司 | 公司高管                     | 住宿定额     | 1500         | 1300         | 900          |\n| 集团公司 | 公司高管                     | 差勤补助定额 | 50           | 25           | 0            |\n| 集团公司 | 平台部门经理                 | 住宿定额     | 600          | 500          | 400          |\n| 集团公司 | 平台部门经理                 | 差勤补助定额 | 200          | 100          | 50           |\n| 集团公司 | 平台专业职高级经理、资深专家 | 住宿定额     | 450          | 350          | 300          |\n| 集团公司 | 平台专业职高级经理、资深专家 | 差勤补助定额 | 100          | 100          | 80           |\n| 集团公司 | 其他员工                     | 住宿定额     | 400          | 300          | 250          |\n| 集团公司 | 其他员工                     | 差勤补助定额 | 180          | 180          | 150          |",
          "output": {
            "table_type": "指标型表格",
            "header_rows": [
              0,
              1
            ],
            "index_col": [
              0,
              1,
              2
            ],
            "units": "人民币",
            "scale": "None"
          }
        }
      ]
    },
    {
      "name": "简单表格",
      "definition": "不以数值为核心的表格。这类表格即使按照长度拆分后也不影响其理解。",
      "required_output": {
        "header": "表头占据的行索引（从0开始计数）",
        "index_col": "列关键标识符所在的列索引（从0开始计数）"
      },
      "examples": [
        {
          "input": "学生信息登记表\n| 姓名 | 性别 | 年龄 | 学历 |\n| ---- | ---- | ---- | ---- |\n| 张三 | 男   | 22   | 本科 |\n| 李四 | 男   | 23   | 本科 |\n| 王梅 | 女   | 24   | 硕士 |",
          "output": {
            "table_type": "简单表格",
            "header": [
              0
            ],
            "index_col": [
              0
            ]
          }
        }
      ]
    },
    {
      "name": "其他表格",
      "definition": "不属于上述两类的任何表格。",
      "required_output": {}
    }
  ],
  "instructions": [
    "首先确定表格属于哪一类。",
    "依据表格类型，参照'categories'字段中的定义来收集必要的输出信息。",
    "确保所有提供的信息准确无误。"
  ],
  "input": "$input"
}
"""

    template_en = template_zh

    def __init__(self, language: Optional[str] = "en", **kwargs):
        super().__init__(language, **kwargs)

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        table_type = None
        table_info = None
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        if isinstance(rsp, dict) and "table_type" in rsp:
            table_type = rsp["table_type"]
            table_info = rsp
        return table_type, table_info
