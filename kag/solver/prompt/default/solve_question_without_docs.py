from string import Template
from typing import List

from kag.common.base.prompt_op import PromptOp


class SolveQuestionWithOutDocs(PromptOp):

    template_zh = """请根据检索到的知识图回答问题“$question”，并结合历史信息进行综合分析。
要求：
1.尽可能直接回答问题，不包括任何其他信息。
2.不要重复问题的内容。
3.根据提供的信息生成答案。如果可能有多个答案，请生成所有答案。
4.如果没有合适的答案，请回答“I don't know”。
历史：
$history
知识图：
$knowledge_graph

答案：
"""

    template_en = """Please answer the question `$question` based on the retrieved knowledge graph, combine historical information for comprehensive analysis.
Requirement:
1. Answer the question as directly as possible, without including any other information.
2. Do not repeat the content of the question.
3. Generate answers based on the provided information. If multiple answers are possible, generate all of them.
4. If there is no suitable answer, answer 'I don't know'.

history:
$history

knowledge graph:
$knowledge_graph

answer:
"""

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["history", "question", "knowledge_graph"]

    def parse_response(self, response: str, **kwargs):
        return response
