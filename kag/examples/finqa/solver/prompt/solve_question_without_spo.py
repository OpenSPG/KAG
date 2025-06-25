from string import Template
from typing import List


from kag.interface import PromptABC


@PromptABC.register("table_solve_question_without_spo")
class SolveQuestionWithOutSPO(PromptABC):

    template_zh = """
# 任务
请根据检索到的相关文档回答问题“$question”，并结合历史信息进行综合分析。

# 要求
1. 给出理由，并回答问题。
2. 不要尝试进行数学计算，而是给出计算公式。
3. 如果没有合适的答案，请回答“I don't know”。

# 历史信息
$history

# 文档
$docs

答案：
""".strip()

    template_en = """
# Task
Please answer the question `$question` based on the retrieved relevant documents, and combine historical information for comprehensive analysis.

# Requirement
1. Provide reasoning and answer the question.
2. Do not attempt mathematical calculations; instead, provide the calculation formula.
3. If there is no suitable answer, respond with "I don't know".

# History
$history

# Docs
$docs

answer:
"""

    def build_prompt(self, variables) -> str:
        return super().build_prompt(variables)

    @property
    def template_variables(self) -> List[str]:
        return ["history", "question", "docs"]

    def parse_response(self, response: str, **kwargs):
        return response
