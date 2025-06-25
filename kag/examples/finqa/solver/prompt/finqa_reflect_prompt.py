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
根据给出的信息改写问题，使得问题可以被解答。

# 提示
根据以下几种情况改写问题：
1. 问题中给出的时间在内容中完全找不到，可以根据内容修改问题中的时间。
2. 注意财年类问题，时间涉及4月，7月，10月的问题，可能修改为对应的财年。
3. 问题中类似during 2003和from 2003 to 2003，可以修改为from 2002 to 2003。

# 输出格式
先输出你的思考过程，最后返回`New question: <new_question>`。
我将在你回答中提取新问题，务必注意返回格式。

# 输入
## 问题
$question
## 信息
$info

# 你的输出
""".strip()

    template_en = """
# Task
Rewrite the question based on the provided information so that it can be answered.

# Instructions
Rewrite the question according to the following scenarios:
1. If the time mentioned in the question cannot be found in the content at all, the time in the question can be modified based on the content.
2. Pay attention to fiscal year-related questions where the time involves April, July, or October; it may be revised to correspond to the relevant fiscal year.
3. If the question contains phrases like "during 2003" or "from 2003 to 2003," consider changing it to "from 2002 to 2003."

# Expected Output
First, provide your thought process, and then return `New question: <new_question>`.
I will extract the new question from your response, so be sure to follow the return format.

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
        answer_flag = "new question:"
        index = response.lower().rfind(answer_flag)
        if index < 0:
            response = response.splitlines()[-1].strip(" *\n")
        else:
            response = response[index + len(answer_flag) :].strip(" *\n")
        return response
