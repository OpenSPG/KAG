from typing import List


from kag.interface import PromptABC


@PromptABC.register("default_summary_question")
class SummaryQuestionWithOutSPO(PromptABC):

    template_zh = """请根据检索到的相关文档回答问题“$question”，并结合历史信息进行综合分析。
要求：
1.不要重复问题的内容。
2.根据提供的信息生成答案。如果可能有多个答案，请生成所有答案。
3.如果没有合适的答案，也需要根据文档信息，分析出相关内容。
4.给出答案的同时，也给出理由
5.输出格式不要换行
历史：
$history
文档：
$docs

答案：
"""

    template_en = """Please answer the question `$question` based on the retrieved relevant documents, and combine historical information for comprehensive analysis.
Requirement:
1.Do not repeat the content of the question.
2.Generate answers strictly based on provided information. If multiple answers are possible, list all plausible answers.
3.If no suitable answer exists, analyze related content based on document information.
4.Provide the answer along with the reasoning.
5.Output format should not have line breaks.

history:
$history

docs:
$docs

answer:
"""

    @property
    def template_variables(self) -> List[str]:
        return ["history", "question", "docs"]

    def parse_response(self, response: str, **kwargs):
        return response
