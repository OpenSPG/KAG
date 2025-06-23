import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("kag_subquestion_think")
class KagSubquestionThinkPrompt(PromptABC):
    template_zh = """你能一步步回答下面的问题吗？如果可以，请用<answer>\\boxed{你的答案}</answer>的格式包裹你的答案。如果不行，就回复说基于我的内部知识，我无法回答这个问题，我需要获取外部知识。
问题: 
$question
"""
    template_en = """Can you answer the following questions step by step? If you can, wrap your answer with <answer>\boxed{your answer}</answer>. If you can't, just reply that based on my internal knowledge, I can't answer this question, I need to retrieve external knowledge. 
Question: 
$question
"""

    @property
    def template_variables(self) -> List[str]:
        return ["question"]

    def parse_response(self, response: str, **kwargs):
        return response
