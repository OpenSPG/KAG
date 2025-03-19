import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_expression_builder")
class TableExpressionBuildr(PromptABC):
    template_zh = """
# Instruction
根据给出的问题和数据，编写python代码，输出问题结果。
为了便于理解，输出从context中提取的数据，输出中间计算过程和结果。
注意严格根据输入内容进行编写代码，不允许进行假设。
如果无法回答问题，print输出：I don't know.

# Output format
直接输出python代码，python版本为3.10，不要包含任何其他信息。
数值结果要求精确到小数点后5位。

# Examples
## 例子1
### Input
#### Question
47000元按照万分之1.5一共612天，计算利息，一共多少钱？
### Output
```python
# 初始本金
principal = 47000

# 利率（万分之1.5）
rate = 1.5 / 10000

# 天数
days = 612

# 计算年利率
annual_rate = rate * 365

# 计算利息
interest = principal * (annual_rate / 365) * days

# 输出总金额（本金+利息）
total_amount = principal + interest

print(f"总金额：{total_amount:.5f}元")
```

# Input
## Question
$question
## Context
$context
## Error
$error
""".strip()

    template_en = """
# Instruction
Write Python code to answer the given question based on the provided data. The code should output the results of the question.
To ensure clarity, extract and print relevant data from the context, as well as intermediate steps and the final result.
Strictly follow the input information when writing the code, and do not make assumptions.
If the question cannot be answered, print: I don't know.

# Output format
Output Python code directly, in Python version 3.10, without including any additional information.
Numeric results must be accurate to five decimal places.

# Examples
## Example 1
### Input
#### Question
If 47,000 yuan is invested at an annual interest rate of 0.015% for 612 days, what is the total amount including interest?
### Output
```python
# Initial principal
principal = 47000

# Interest rate (0.015% daily)
rate = 1.5 / 10000

# Number of days
days = 612

# Calculate the annualized rate
annual_rate = rate * 365

# Calculate interest
interest = principal * (annual_rate / 365) * days

# Output total amount (principal + interest)
total_amount = principal + interest

print(f"Total amount: {total_amount:.5f} yuan")
```

# Input
## Question
$question
## Context
$context
## Error
$error
""".strip()

    @property
    def template_variables(self) -> List[str]:
        return ["question", "context", "error"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = rsp.strip("```").strip("python")
        return rsp
