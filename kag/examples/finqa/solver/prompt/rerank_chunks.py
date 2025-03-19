import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_rerank_chunks")
class TableRerankChunksPrompt(PromptABC):

    template_zh = """
# Task
选择对回答子问题最有帮助的chunks，返回chunk编号列表。
如果没有合适的chunk，返回none。

# Output format
给出你的理由，最后一行返回`The final answer is: <chunk编号1>, <chunk编号2>`。
chunk编号不要包含任何其他字符。

# Input
## Question and context
Question: $question
Context: $context

## Waiting for selected chunks
$chunks

# Your Selection

""".strip()

    template_en = """
# Task
Select the most helpful chunks for the question and return the chunk numbers.
If no suitable chunk is found, return None.

# Output format
Give your reason, and return `The final answer is: <chunk_number1>, <chunk_number2>` in the last line.
The chunk number should not contain any other characters.

# Input
## Question and context
Question: $question
Context: $context

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
            numbers = re.findall(r"\d+", response)
            int_list = [int(num) for num in numbers]
            return int_list
        except Exception as e:
            logger.warning(f"{response} parse logic form faied {e}", exc_info=True)
            return None
