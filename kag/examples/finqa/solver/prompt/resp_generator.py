import re
from string import Template
from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_resp_generator")
class FinQARespGenerator(PromptABC):
    template_zh = """
# 任务
从给定的信息中，提取问题答案。
输出数值答案，以`Finanl Answer: <number>`作为结束。

# 注意事项
答案从Math计算结果中提取，你不允许进行计算。
答案不需要包含单位，只输出数字。
数值应精确到小数点后5位。
是否类问题，返回yes或no。

# 给定的信息
问题：$instruction
解题过程：
```
$memory
```

# 你的答案
"""
    template_en = """
# Task
Extract the answer to the question from the provided information.
Output the numerical answer, ending with `Final Answer: <number>`.

# Notes
The answer should be extracted directly from the math calculation results; you are not allowed to perform any calculations.
The answer does not need to include units, only the number should be output.
The numerical value should be precise to five decimal places.
For yes-or-no type questions, return either "yes" or "no."

# Given Information
Question: $instruction
Solution process:
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
        response = response[index + len(answer_flag) :].strip(" *\n")
        try:
            tmp = float(response)
        except:
            if "yes" in response.lower():
                return "yes"
            elif "no" in response.lower():
                return "no"
            else:
                return response
        return response
