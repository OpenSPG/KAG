import logging
import re
from typing import List

from kag.solver.prompt import RetrieverLFStaticPlanningPrompt

logger = logging.getLogger(__name__)

from kag.interface import PromptABC


@PromptABC.register("supplychain_lf_plan")
class LogicFormPlanPrompt(RetrieverLFStaticPlanningPrompt):
    default_case_zh = [
        {
            "query": "A溃坝事件对那些公司产生了影响",
            "answer": "Step1:查询A溃坝事件引起的公司事件\nAction1:get_spo(s=s1:产业链事件[A溃坝事件], p=p1:导致, o=o1:公司事件)\nOutput:输出o1\nAction2:get(o1)",
        }
    ]

    default_case_en = default_case_zh
