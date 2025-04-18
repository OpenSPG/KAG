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
from typing import List
from kag.interface import PromptABC


@PromptABC.register("judger_prompt")
class JudgerPrompt(PromptABC):

    template_zh = """
    {
        "instruction": "你是一个擅长问答和评分的人工智能助手。提供一个问题及其正确答案(gold)，你的任务是分析给定的预测(prediction)是否正确，预测（prediction）中允许有冗余表达。请以 JSON 字符串的格式回答。你可以参考示例进行提取。",
        "example": [
            {
                "question": "2岁到青春前期，体重每年增加（　　）。{"A": "0.5kg", "B": "1kg", "C": "1.5kg", "D": "2kg", "E": "2.5kg"}",
                "gold": "D、2kg",
                "prediction": "2kg。理由是引用中提到：2 岁至青春前期体重增长减慢，年增长值约 2kg",
                "judgment": "true"
            }, {
                "question": "35岁前心脏性猝死的主要原因是（　　）。{"A": "心肌病", "B": "心脏瓣膜病", "C": "心包炎", "D": "长QT综合征", "E": "先天性心脏病"}",
                "gold": "A、心肌病",
                "prediction": "B、心脏瓣膜病",
                "judgment": "false"
            }
        ],
        "question": "$question",
        "gold": "$gold",
        "prediction": "$prediction",
    }
        """

    template_en = template_zh

    def __init__(self, language: str = "", **kwargs):
        super().__init__(language, **kwargs)

    @property
    def template_variables(self) -> List[str]:
        return ["question", "gold", "prediction"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "judgment" in rsp:
            rsp = rsp["judgment"]

        return rsp
