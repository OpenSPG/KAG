import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_decomposition_query")
class AtomicQueryPlanPrompt(PromptABC):
    template_zh = f"""# Task
Your task is to analyse the providing context then raise atomic sub-questions for the knowledge that can help you answer the question better. Think in different ways and raise as many diverse questions as possible.

# Output Format
Please output in following JSON format:
{{
    "thinking": <A string. Your thinking for this task, including analysis to the question and the given context.>,
    "sub_questions": <A list of string. The sub-questions indicating what you need.>
}}

# Context
The context we already have:
$content

# Question
$query

# Your Output:"""

    template_en = f"""# Task
Your task is to analyse the providing context then raise atomic sub-questions for the knowledge that can help you answer the question better. Think in different ways and raise as many diverse questions as possible.

# Output Format
Please output in following JSON format:
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
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "sub_questions" in rsp:
            entities = rsp["sub_questions"]
        else:
            entities = rsp

        return entities
