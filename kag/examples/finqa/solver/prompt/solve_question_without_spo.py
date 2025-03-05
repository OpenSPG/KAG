from string import Template
from typing import List


from kag.interface import PromptABC


@PromptABC.register("table_solve_question_without_spo")
class SolveQuestionWithOutSPO(PromptABC):

    template_zh = """
# 任务
回答子问题“$question”。

# 要求
1. 充分分析给你的信息，包括父问题，历史问答信息，以及检索到的文档。
2. 不要尝试进行数学计算，而是给出计算公式。
3. 如果没有合适的答案，请回答“I don't know”。

# 输出格式
** 理由: ** <输出你的理由>
** 答案: ** <子问题的答案>

# 父问题以及历史信息
父问题：$parent_question
历史问答：$history

# 文档
$docs

你的答案：
""".strip()

    template_en = """
# Task
Answer the sub-question "$question".

# Requirements
1. Fully analyze the information provided to you, including the parent question, historical Q&A information, and retrieved documents.
2. Do not attempt mathematical calculations; instead, provide a calculation formula.
3. If no suitable answer can be found, reply with "I don't know."

# Output Format
** Reason: ** <Provide your reasoning>
** Answer: ** <Answer to the sub-question>

# Parent Question and Historical Information
Parent Question: $parent_question
Historical Q&A: $history

# Documents
$docs

Your Answer:
""".strip()

    def build_prompt(self, variables) -> str:
        return super().build_prompt(variables)

    @property
    def template_variables(self) -> List[str]:
        return ["history", "question", "docs", "parent_question"]

    def parse_response(self, response: str, **kwargs):
        return response