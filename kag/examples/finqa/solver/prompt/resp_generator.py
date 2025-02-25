import re
from string import Template
from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_resp_generator")
class FinQARespGenerator(PromptABC):
    template_zh = """
基于给定的信息回答问题。
输出理由，最终直接给出数字答案，以`Finanl Answer: <number>`作为结束。

给定的信息：
```
$memory
```
问题：'$instruction'

你的答案：
"""
    template_en = """
Answer the question based on the given information.
Give the reason, and finally give the number answer directly, ending with `Final Answer: <number>`.

The following are given information:
```
$memory
```

Question: '$instruction'

Your answer:
"""

    @property
    def template_variables(self) -> List[str]:
        return ["memory", "instruction"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        answer_flag = "Final Answer:"
        index = response.rfind(answer_flag)
        response = response[index + len(answer_flag) :].strip()
        return response
