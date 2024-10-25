import logging

from kag.solver.prompt.default.logic_form_plan import LogicFormPlanPrompt

logger = logging.getLogger(__name__)



class LawLogicFormPlanPrompt(LogicFormPlanPrompt):
    default_case_zh = """"cases": [
        {
            "query": "中华人民共和国铁路法第二十八条的内容是什么",
            "answer": "Step1:中华人民共和国铁路法第二十八条的内容是什么 ?\nAction1:get_spo(s=s1:Chunk[中华人民共和国铁路法第二十八条], p=p1:content, o=o1:Text)\n Action2: get(o1)"
        }
    ],"""

    template_en = LogicFormPlanPrompt.template_en

    def __init__(self, language: str):
        super().__init__(language)
