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


@PromptABC.register("labor_law_background_extra")
class TargetJudge(PromptABC):
    template_zh = (
        "你是一个法律专家，根据用户的对话记录，抽取出其中的法律事实"
        "只输出事实，不要做解释或者回答，如果存在多个，则使用;分割"
        "示例:"
        "User:我上班途中受伤了，交警认定对方全责，能认定工伤吗？"
        "output: 咨询者在上班途中遇到车祸; 对方全责"
        "对话记录:\n$history_qa"
    )
    template_en = (
        "Judging based solely on the current known information and without allowing for inference, "
        "are you able to completely and accurately respond to the question '$instruction'? "
        "\nKnown information: '$memory'. "
        "\nIf you can, please reply with 'Yes' directly; "
        "if you cannot and need more information, please reply with 'No' directly."
    )

    @property
    def template_variables(self) -> List[str]:
        return ["history_qa"]
    def parse_response(self, response: str, **kwargs):
        return response
