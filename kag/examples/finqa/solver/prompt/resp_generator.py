import re
from string import Template
from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_resp_generator")
class FinQARespGenerator(PromptABC):
    template_zh = """
# Task
基于给定的信息回答问题。
先输出理由，最终给出数值答案，以`Finanl Answer: <number>`作为结束。

# 注意事项
如果问百分比，给出带有百分号的数值，如`Final Answer: 0.5%`。
数值精度要求越高越好。

# 给定的信息
问题：'$instruction'
```
$memory
```

# 你的答案
"""
    template_en = """
# Task
Based on the given information, answer the question.
First, provide the reasoning, and then give the final numerical answer, ending with `Final Answer: <number>`.

# Notes
If the question asks for a percentage, provide the value with a `%` sign, such as `Final Answer: 0.5%`.
Ensure the numerical precision is as high as possible.

# Given Information
Question: '$instruction'
```
$memory
```

# Your Answer
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
