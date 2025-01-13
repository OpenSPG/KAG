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

from typing import Optional, List
from kag.interface import PromptABC
import ast


@PromptABC.register("outline_align")
class OutlineAlignPrompt(PromptABC):
    template_zh = """
{
    "instruction": "请分析以下大纲列表，统一调整标题的层级。遵循以下规则：
1. 相同类型的标题应该有相同的层级，例如所有'第X章'都应该是同一层级
2. 层级关系应该符合逻辑，例如:
   - 章(1级) > 节(2级) > 条(3级)
   - 部分(1级) > 章(2级) > 节(3级)
3. 考虑标题的上下文关系，确保层级的连贯性
4. 如果标题不含明确的层级标识，根据其内容和上下文推断合适的层级

请务必按照以下格式返回，不要返回其他任何内容，请返回调整后的大纲列表，格式为:
[(标题1, 层级1), (标题2, 层级2), ...]

输入的大纲列表为:
$outlines",
    "example": [
        {
            "input": [
                ("第一章 绪论", 2),
                ("第一节 研究背景", 1),
                ("第二章 文献综述", 1),
                ("第二节 研究方法", 2)
            ],
            "output": [
                ("第一章 绪论", 1),
                ("第一节 研究背景", 2),
                ("第二章 文献综述", 1),
                ("第二节 研究方法", 2)
            ]
        }
    ]
}
"""

    template_en = """
{
    "instruction": "Please analyze the following outline list and unify the levels of titles according to these rules:
1. Similar types of titles should have the same level (e.g., all 'Chapter X' should be at the same level)
2. Level relationships should follow logic, e.g.:
   - Chapter(1) > Section(2) > Article(3)
   - Part(1) > Chapter(2) > Section(3)
3. Consider context relationships between titles to ensure level continuity
4. For titles without clear level indicators, infer appropriate levels based on content and context

Please return the adjusted outline list in the format:
[(title1, level1), (title2, level2), ...]

Input outline list:
$outlines",
    "example": [
        {
            "input": [
                ("Chapter 1 Introduction", 2),
                ("Section 1.1 Background", 1),
                ("Chapter 2 Literature Review", 1),
                ("Section 2.1 Methods", 2)
            ],
            "output": [
                ("Chapter 1 Introduction", 1),
                ("Section 1.1 Background", 2),
                ("Chapter 2 Literature Review", 1),
                ("Section 2.1 Methods", 2)
            ]
        }
    ]
}
"""

    def __init__(self, language: Optional[str] = "zh"):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["outlines"]

    def parse_response(self, response: str, **kwargs):
        if isinstance(response, str):
            cleaned_data = response.strip("`python\n[] \n")
            cleaned_data = "[" + cleaned_data + "]"
            return ast.literal_eval(cleaned_data)
        if isinstance(response, dict) and "output" in response:
            return response["output"]
        return response
