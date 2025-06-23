import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("kag_generate_answer")
class KagGenerateAnswerPrompt(PromptABC):
    template_zh = """根据问题、前n个子问题及其答案（由#n表示）来回答最后一个子问题。请用<answer>\\boxed{你的答案}</answer>的格式包裹你的答案。 
问题:
$question
子问题:
$sub_questions
最后一个子问题:
$last_question
输出:"""
    template_en = """Answer the last question based on question, the first n sub-questions and their answers (indicated by #n), and wrap the result with <answer>\\boxed{your answer}</answer>. 
question:
$question
sub-questions:
$sub_questions
last-question:
$last_question
answer:
"""

    @property
    def template_variables(self) -> List[str]:
        return ["last_question", "sub_questions", "question"]

    def parse_response(self, response: str, **kwargs):
        return response
