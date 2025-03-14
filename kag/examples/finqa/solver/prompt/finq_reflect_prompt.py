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


@PromptABC.register("finqa_reflect_question")
class FinQAReflectQuestion(PromptABC):
    template_zh = """
# 任务
根据给出的信息改写问题。

# 提示
根据以下几种情况改写问题：
1. 问题中给出的时间与内容不符，修改问题中的时间。
2. 注意一些公司的财年从年中开始，涉及这种情况修改问题中时间来适配财年时间。
3. 注意12月31日，即为下一年的开始，涉及这种情况的，修改问题中时间，以适配信息中的时间。

# 返回
先输出你的思考过程，最后返回`New question: <new_question>`。

# 输入
## 问题
$question
## 信息
$info

# 你的输出
""".strip()

    template_en = """
# Task
Rewrite the question based on the provided information.

# Instructions
Rewrite the question according to the following scenarios:
1. If the time mentioned in the question does not match the content, adjust the time in the question.
2. Be aware that some companies have fiscal years starting mid-year; for such cases, modify the time in the question to align with the fiscal year.
3. Note that December 31st is effectively the start of the next year; in such cases, adjust the time in the question to match the provided information.

# Expected Output
First, provide your thought process, and then return `New question: <new_question>`.

# Input
## Question
$question
## Information
$info

# Your Output
""".strip()

    @property
    def template_variables(self) -> List[str]:
        return ["question", "info"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        answer_flag = "New question:"
        index = response.rfind(answer_flag)
        response = response[index + len(answer_flag) :].strip(" *\n")
        return response
