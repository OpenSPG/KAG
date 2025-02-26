import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_rerank_chunks")
class TableRerankChunksPrompt(PromptABC):

    template_zh = """
# Task
选择对问题最有帮助的一个chunk，返回chunk编号。

# Output format
给出你的理由，最后一行返回`The final answer is: <chunk编号>`。
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
Select the most helpful chunk for the question and return the chunk number.

# Output format
Give your reason, and return `The final answer is: <chunk_number>` in the last line.
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
            response = response.strip(" .<>'")
            if "none" in response.lower():
                return None
            if "," in response:
                response = response.split(",")[0].strip()
            if "and" in response:
                response = response.split("and")[0].strip()
            response = response.strip(" .<>'*")
            return int(response)
        except Exception as e:
            logger.warning(f"{response} parse logic form faied {e}", exc_info=True)
            return None
