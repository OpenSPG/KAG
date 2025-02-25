import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_rerank_chunks")
class TableRerankChunksPrompt(PromptABC):

    template_zh = """
# Task
你的任务是选择与问题最相关的chunk，返回chunk的编号。

# Output format
给出你的理由，最后一行返回`The final answer is: <chunk编号>`。

# Input
## Question
$question

## context
$context

## Chunks
$chunks

# Your Answer

""".strip()

    template_en = """
# Task
Your task is to select the most relevant chunk to the question and return the number of the chunk.

# Output format
Give your reason, and return `The final answer is: <chunk_number>` in the last line.

# Input
## Question
$question

## context
$context

## Chunks
$chunks

# Your Answer
""".strip()

    @property
    def template_variables(self) -> List[str]:
        return ["question", "chunks"]

    def parse_response(self, response:str, **kwargs):
        try:
            logger.debug(f"logic form:{response}")
            ans_flag = "The final answer is:"
            index = response.rfind(ans_flag)
            response = response[index + len(ans_flag):]
            response = response.strip(" .<>")
            return int(response)
        except Exception as e:
            logger.warning(f"{response} parse logic form faied {e}", exc_info=True)
            return None
