import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_expression_builder")
class FinQAExpressionBuildr(PromptABC):
    template_zh = """
# 任务
你是一个财经领域的专家，根据给出的问题和信息，编写python代码，输出问题结果。
注意严格根据输入内容进行编写代码，不允许进行假设。
如果无法回答问题，print输出：I don't know.

# 一些解决问题的思路
$examples

# 输出格式
直接输出python代码，python版本为3.10，不要包含任何其他信息。
数值结果要求精确到小数点后5位。

# 例子
## Input
### Question
47000元按照万分之1.5一共612天，计算利息，一共多少钱？
## Output
```python
# total_amount计算过程，略
print(f"总金额：{total_amount:.5f}")
```

# 真正的输入
## 问题
$question
## 参考信息
$context
## 之前的错误
$error
""".strip()

    template_en = """
# Task
You are an expert in the field of finance. Based on the provided questions and information, write Python code to output the results of the questions.
Note that you must strictly follow the input content to write the code without making any assumptions.
If the question cannot be answered, use print to output: I don't know.

# Some problem-solving ideas
$examples

# Output Format
Output only the Python code directly, using Python version 3.10, without including any other information.
Numerical results should be accurate to 5 decimal places.

# Example
## Input
### Question
Calculate the interest for 47,000 yuan at 0.015% for 612 days, and determine the total amount.
## Output
```python
# Calculation process for total_amount, omitted
print(f"Total Amount: {total_amount:.5f}")
```

# Actual Input
## Question
$question
## Reference Information
$context
## Previous Errors
$error
""".strip()

    @property
    def template_variables(self) -> List[str]:
        return ["question", "context", "error", "examples"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = rsp.strip("```").strip("python")
        return rsp
