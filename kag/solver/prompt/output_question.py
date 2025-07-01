from typing import List


from kag.interface import PromptABC


@PromptABC.register("default_output_question")
class OutputQuestionPrompt(PromptABC):

    template_zh = """请根据检索到的相关文档回答问题“$question”，并结合历史信息进行综合分析。
要求：
1.不要重复问题的内容。
2.根据提供的信息生成答案。如果可能有多个答案，请生成所有答案。
3.如果没有合适的答案，也需要根据文档信息，分析出相关内容。
4.如果上下文为空，则根据模型内部知识进行回答
5.输出时按照类似这样的句式生成“根据问题，我首先考虑到xxx，其次考虑yyy，最后zzz，综上，所以mmmm”
6.出语调要求通顺，不要有机械感
上下文：
$context

答案：
"""

    template_en = """Please answer the question “$question” based on the retrieved relevant documents and combine it with historical information for comprehensive analysis. The requirements are as follows:
1.Do not repeat the content of the question.
2.Generate answers based on the provided information. If there are multiple possible answers, generate all of them.
3、If there is no suitable answer, analyze relevant content based on the document information.
4.If the context is empty, respond based on the model's internal knowledge.
5.When outputting, use a sentence structure similar to this: "Based on the question, I first considered xxx, then yyy, and finally zzz. In conclusion, therefore mmmm."
6.The tone of the response should be smooth and natural, avoiding any mechanical feel.

Context: 
$context

Answer:
"""

    @property
    def template_variables(self) -> List[str]:
        return ["context", "question"]

    def parse_response(self, response: str, **kwargs):
        return response
