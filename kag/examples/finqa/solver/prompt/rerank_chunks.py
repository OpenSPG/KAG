import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_rerank_chunks")
class TableRerankChunksPrompt(PromptABC):

    template_zh = """
# Task
你是一个财务专家，针对给出的问题，选择对解答问题最有帮助的chunk，返回chunk编号。
如果子问题答案存在矛盾，分析引用的原文，以原文为准。

# Output format
给出你的思考，最后一行返回`The final answer is: <chunk编号1>, <chunk编号2>`。
chunk编号不要包含任何其他字符。

# Input
## Question and Selected chunks
Question: $question
Chunks:
$context

## Waiting for selected chunks
$chunks

# Your Selection

""".strip()

    template_en = """
# Task
You are a financial expert. For the given question, select the chunk(s) that are most helpful in addressing and solving the problem and provide the corresponding chunk number(s). 
If there are contradictions in the answers to sub-questions, analyze the referenced original text and rely on the original content for correctness.

# Output format
Give your reasoning, and on the last line, return `The final answer is: <chunk_number1>, <chunk_number2>`.
The chunk number should not contain any other characters.

# Input
## Question and Selected chunks
Question: $question
Chunks:
$context

## Waiting for selected chunks
$chunks

# Your Selection
""".strip()

    @property
    def template_variables(self) -> List[str]:
        return ["question", "chunks", "context"]

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
            numbers = [int(num) if "." not in num else float(num) for num in matches]
            return numbers
        except Exception as e:
            logger.warning(f"{response} parse logic form faied {e}", exc_info=True)
            return None
