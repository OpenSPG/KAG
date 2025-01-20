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


@PromptABC.register("labor_law_cot_plan")
class LawCotJudge(PromptABC):
    template_zh = (
        """你是一个法律专家，根据输入的信息给出一个解决这个法律问题的规划步骤
要求：给出思考问题步骤，不需要给出理由和法律依据
示例1:
输入信息
User：我可以休带薪年休假吗？
background:
带薪年休假咨询
target:
用户咨询自身是否符合休带薪年休假条件
思考步骤:
1、是否享有法定年休假？
2、剩余未休法定年休假的天数？
3、根据剩余年休假天数、薪资信息，未休年假工资如何折算？
示例2:
输入信息
chat:
User:你好,我想咨询一下,我在一家公司工作了3个月,但没有签劳动合同,现在公司想辞退我,我想知道我们之间是否存在劳动关系?
background:
咨询者在一家公司工作了3个月; 未签订劳动合同; 公司想辞退咨询者
target:
用户期望确认是否存在劳动关系
思考步骤:
1、确认双方主体是否适用劳动法主体资格
2、若符合劳动法主体资格，则确认是否存在事实劳动关系
3、若符合事实劳动关系，则确认未签订劳动合同的过错方
4、根据过错方认定责任

"""
        "现在输入信息"
        "$memory"
        "$instruction"
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
        return ["memory", "instruction"]
    def parse_response(self, response: str, **kwargs):
        return response
