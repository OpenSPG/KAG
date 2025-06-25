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
from typing import List
from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_resp_judge")
class FinQARespJudge(PromptABC):
    template_zh = """
# 任务
你是金融领域专家，针对给出的问题，和解答过程，判断答案是否正确。
你需要判断python代码中的计算过程是否正确，特别需要注意计算中使用的数值是否与问题相匹配。
你的判断标准要尽可能严格。

# 输出格式
输出你的思考过程，并在最后一行输出
`The process of answering this question is correct`
或
`The process of answering this question is incorrect`

# 问题
$instruction

# 解答过程
$memory
""".strip()

    template_en = """
# Task
You are an expert in the financial domain. For the given problem and the solution process, determine whether the answer is correct.
You need to evaluate whether the calculation process in the Python code is accurate, paying particular attention to whether the values used in the computation match the problem's requirements.
Your judgment criteria should be as strict as possible.

# Output Format
Provide your reasoning process, and on the last line, state:
`The process of answering this question is correct`
or
`The process of answering this question is incorrect`

# Question
$instruction

# Answering Process
$memory
"""

    @property
    def template_variables(self) -> List[str]:
        return ["memory", "instruction"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        if (
            "The process of answering this question is correct".lower()
            in response.lower()
        ):
            return True
        return False
