import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("atomic_query_decomposition_prompt")
class AtomicQueryPlanPrompt(PromptABC):
    template_zh = f"""# 任务
你的任务是分析给定上下文信息，判断是否已经能够回答给出的question。如果不能，请为当前问题提出一组原子性的子问题，这些原子问题能够帮助你更好的回答问题，补全回答问题所需的信息。你需要从不同角度进行思考，并且尽可能的提出多样化的问题。
需要注意的是，原子问题之间尽量避免出现答案的依赖关系。如果已经上下文信息已经可以准确回答问题，sub_questions可以是空列表。

# 输出格式
请严格按照以下json格式进行输出：
{{
    "thinking": <A string. Your thinking for this task, including analysis to the question and the given context.>,
    "sub_questions": <A list of string. The sub-questions indicating what you need.>
}}

# 上下文信息
我们已经有的上下文信息：
$content

# 问题
$query

# 你的输出:"""

    template_en = f"""# Task
Your task is to analyze the given contextual information and determine if the available information can answer the given question. If it does not answer the question, analyze the missing information and extract a set of sub-questions for the needed problem question that will help you answer the question better. You need to think in different ways and ask as many diversity questions as possible. If the contextual information is already available to answer the question directly, then it can be returned as empty.

# Output format
Please strictly follow the json format below:
{{
    "thinking": <A string. Your thinking for this task, including analysis to the question and the given context.>,
    "sub_questions": <A list of string. The sub-questions indicating what you need.>
}}

# Context
The context we already have:
$context

# Question
$query

# Your Output:"""

    @property
    def template_variables(self) -> List[str]:
        return ["query", "context"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            try:
                rsp = json.loads(rsp.strip('```json').strip('```'))
            except Exception as e:
                print(f"[QuestionDecompositionParser] content to decode: {rsp}")
                print(f"Exception: {e}")
                return "", []
        if isinstance(rsp, dict) and "sub_questions" in rsp:
            thinking  = rsp["thinking"]
            sub_questions = rsp["sub_questions"]
        return thinking, sub_questions
