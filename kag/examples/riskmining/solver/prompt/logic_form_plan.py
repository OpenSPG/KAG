import logging
import re
from typing import List

from kag.solver.prompt import RetrieverLFStaticPlanningPrompt

logger = logging.getLogger(__name__)

from kag.interface import PromptABC


@PromptABC.register("riskmining_lf_plan")
class LogicFormPlanPrompt(RetrieverLFStaticPlanningPrompt):

    default_case_zh = [
        {
            "Action": "张*三是一个赌博App的开发者吗?",
            "answer": "Step1:查询是否张*三的分类\nAction1:get_spo(s=s1:自然人[张*三], p=p1:属于, o=o1:风险用户)\nOutput:输出o1\nAction2:get(o1)",
        }
    ]

    default_case_en = default_case_zh
