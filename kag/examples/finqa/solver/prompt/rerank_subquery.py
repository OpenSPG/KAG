import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_rerank_subquery")
class TableRerankSubqueryPrompt(PromptABC):

    template_zh = """
# Task
你是一个财务专家，针对给出的问题，选择对解答问题最有帮助的子问题，返回子问题编号。
根据原文仔细判断子问题答案是否正确，不要选择你认为错误的子问题。

# Output format
给出你的思考过程，最后一行返回`The final answer is: <chunk编号1>, <chunk编号2>`。
chunk编号不要包含任何其他字符。

# Input
## Question
Question: $question

## Waiting for selected sub-question
$chunks

# Your Selection

""".strip()

    template_en = """
# Task
You are a financial expert. For the given question, select the sub-questions (chunks) that are most helpful in solving the question, and return their chunk numbers.
Carefully evaluate the answers to the sub-questions based on the original content, and do not select chunks that you believe are incorrect.

# Output format
Provide your reasoning process, and in the last line, return `The final answer is: <chunk number 1>, <chunk number 2>`.
Chunk numbers should not contain any additional characters.

# Input
## Question
Question: $question

## Waiting for selected sub-question
$chunks

# Your Selection
""".strip()

    @property
    def template_variables(self) -> List[str]:
        return ["question", "chunks"]

    def parse_response(self, response: str, **kwargs):
        try:
            logger.debug(f"logic form:{response}")
            ans_flag = "The final answer is:"
            index = response.rfind(ans_flag)
            response = response[index + len(ans_flag) :]
            if "none" in response.lower():
                logger.error(f"{response}")
                return None
            pattern = r"\d+\.?\d*"
            matches = re.findall(pattern, response)
            numbers = [int(num) for num in matches]
            return numbers
        except Exception as e:
            logger.warning(f"{response} parse logic form faied {e}", exc_info=True)
            return None
