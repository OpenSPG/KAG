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


@PromptABC.register("default_llm_accuracy_judge")
class LlmAccuracyJudge(PromptABC):
    template_zh = """
    #任务
    你的任务是判断给定问题的预测答案是否和该问题的标准答案一致。\n如果一致，请直接回复‘是’\n如果不一致，请直接回复‘否’，不要输出任何无关内容。
    
    #问题
    $question
    
    #标准答案
    $gold
    
    #预测答案
    $predication
    
    #你的输出
    """
    template_en = """#task
    Your task is to determine whether the predicted answer to a given question is consistent with the standard answer to that question. \n If it is consistent, please respond directly with 'yes' \n If it is not consistent, please respond directly with 'no' and do not output any irrelevant content.
    
    #question
    $question
    
    #Standard answer
    $gold
    
    #Predicted answer
    $prediction
    
    #Your output"""

    @property
    def template_variables(self) -> List[str]:
        return ["question", "gold","prediction"]

    def parse_response(self, satisfied_info: str, **kwargs):
        if satisfied_info[:3] == "Yes" or satisfied_info[:3] == "yes":
            if_finished = True
        else:
            if_finished = False
        return if_finished
