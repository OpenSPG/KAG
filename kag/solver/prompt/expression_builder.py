import logging
from typing import List

from kag.common.utils import get_now
from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_expression_builder")
class ExpressionBuildr(PromptABC):
    template_zh = (
        f"今天是{get_now(language='zh')}。"
        + """
# instruction
根据给出的问题和数据，编写python代码，输出问题结果。
从context中提取的数据必须显式赋值，所有计算步骤必须用代码实现，不得隐含推断。
必须输出中间计算过程和结果，格式为print语句。
如果context未提供必要数据或无法计算，直接打印"I don't know."

# output format
严格输出以下结构的python代码（版本3.10）：
1. 数据提取部分：代码中涉及输入的数值需要从context及question中提取，不允许进行假设
2. 计算过程：分步实现所有数学运算，每个步骤对应独立变量
3. 输出：每个中间变量和最终结果必须用print语句输出

# examples
## 例子1
### input
#### question
4百万元按照日利率万分之1.5，一共612天，计算利息，一共多少钱？
#### context
日利率万分之1.5
### output
```python
# 初始本金（单位：百万）
principal = 4  # 单位：百万

# 日利率计算（万分之1.5）
daily_rate = 1.5 / 10000

# 计算周期
days = 612

# 单日利息计算
daily_interest = principal * daily_rate

# 累计利息计算
total_interest = daily_interest * days

# 总金额计算
total_amount = principal + total_interest

print(f"单日利息：{daily_interest:.2f}百万")
print(f"累计利息：{total_interest:.2f}百万")
print(f"总金额：{total_amount:.2f}百万")
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

## 例子3
### input
#### question
47000元按照612天计算利息，本息一共多少钱？
#### content

### output
```python
# 未给出利率，无法计算
print("未给出利率，无法计算")
```
# input
## question
$question
## context
$context
## error
$error
## output
"""
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
