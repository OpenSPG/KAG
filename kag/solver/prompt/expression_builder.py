import logging
from typing import List

from kag.common.utils import get_now
from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_expression_builder")
class ExpressionBuildr(PromptABC):
    template_zh = (
        f"今天是{get_now(language='zh')}。"
        + """\n# instruction
根据给出的问题和数据，编写python代码，输出问题结果。
为了便于理解，输出从context中提取的数据，输出中间计算过程和结果。
注意严格根据输入内容进行编写代码,不允许进行假设
例如伤残等级如果context中未提及,则认为没有被认定为残疾
如果无法回答问题，直接返回：I don't know.

# output format
直接输出python代码，python版本为3.10，不要包含任何其他信息

# examples
## 例子1
### input
#### question
47000元按照万分之1.5一共612天，计算利息，一共多少钱？
### output
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

print(f"总金额：{total_amount:.2f}元")
```

## 例子2
### input
#### question
根据2018年和2019年游戏收入，计算2019年游戏收入增长率；再根据增长率，计算2020年游戏收入
#### context
2018年游戏收入是1300万，2019年游戏收入是1580万
### output
```python
# 2018年和2019年的游戏收入（单位：万）
revenue_2018 = 1300
revenue_2019 = 1580

# 计算2019年的收入增长率
growth_rate = (revenue_2019 - revenue_2018) / revenue_2018
print(f"2019年的收入增长率为: {growth_rate * 100:.2f}%")

# 根据增长率计算2020年的收入
revenue_2020 = revenue_2019 * (1 + growth_rate)
print(f"2020年的预计收入为: {revenue_2020:.2f}万")
```

# input
## question
$question
## context
$context
## error
        $error"""
    )
    template_en = (
        f"Today is {get_now(language='en')}。\n"
        + """# instruction
Generate Python code based on the given question and context data to output the result. 
Show extracted data from context, intermediate calculations and final results for clarity.
Strictly use input content without making assumptions (e.g., if disability grade isn't mentioned, assume no disability).
Return "I don't know." if question cannot be answered.

# output format
Output only Python 3.8 code without any additional information

# examples
## Example 1
### input
#### question
Calculate interest for 47,000元 at 0.015% daily rate over 612 days
### output
```python
# Initial principal
principal = 47000

# Daily rate (0.015‰)
rate = 1.5 / 10000

# Days
days = 612

# Calculate annual rate
annual_rate = rate * 365

# Calculate interest
interest = principal * (annual_rate / 365) * days

# Calculate total
total = principal + interest

print(f"Total amount: {total:.2f} yuan")
```
## Example 2
### input
#### question
Calculate 2019 game revenue growth rate and predict 2020 revenue based on 2018-2019 data
#### context
2018 game revenue: 13M, 2019 game revenue: 15.8M
### output
```python
# 2018-2019 revenue (million)
revenue_2018 = 1300
revenue_2019 = 1580

# Calculate growth rate
growth_rate = (revenue_2019 - revenue_2018) / revenue_2018
print(f"Growth rate: {growth_rate*100:.2f}%")

# Predict 2020 revenue
revenue_2020 = revenue_2019 * (1 + growth_rate)
print(f"2020 projected revenue: {revenue_2020:.2f} million")
```

# input
## question
$question
## context
$context
## error
$error
    """
    )

    @property
    def template_variables(self) -> List[str]:
        return ["question", "context", "error"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = rsp.strip().strip("```").strip("python")
        return rsp
