import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_expression_builder")
class FinQAExpressionBuildr(PromptABC):
    template_zh = """
# 任务
你是一位财经领域的专家。根据提供的问题和相关信息，编写 Python 代码以输出问题的答案。

# 注意事项
1. 严格依据输入内容：不得进行任何假设或添加额外信息。
2. 答案格式：
- 如果问题是“是否类问题”，输出 yes 或 no。
- 其他问题的答案必须是一个数字，且数值需精确到小数点后 5 位。
3. 输出要求：
- 使用 print 输出答案时，应尽量附带完整的描述信息，以明确该数字的含义。
4. 无法回答的情况：
- 如果根据提供的信息无法得出答案，print 输出：I don't know.

# 可参考的解题思路
```
$examples
```

# 输出格式
直接输出python代码，python版本为3.10，不要包含任何其他信息。

# 例子
## Input
### Question
in 2010 and 2009, what was the total fair value in billions of ...?
## Output
```python
total_fair_value_2009 = ...
total_fair_value_2010 = ...
# total_fair_value
total_fair_value = total_fair_value_2009 + total_fair_value_2010
print(f"公允价值总额：{total_fair_value:.5f}")
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
You are an expert in the field of finance. Based on the provided questions and relevant information, write Python code to output the answers to the questions.

# Notes
1. Strictly adhere to the input content: Do not make any assumptions or add extra information.
2. Answer format:
   - If the question is a "yes/no" type, output `yes` or `no`.
   - For other types of questions, the answer must be a number, accurate to 5 decimal places.
3. Output requirements:
   - When using `print` to output the answer, include a complete description to clearly indicate the meaning of the number.
4. Unanswerable cases:
   - If the answer cannot be derived from the provided information, output via `print`: `I don't know.`

# Possible problem-solving strategies for reference
```
$examples
```

# Output Format
Output only the Python code directly, using Python version 3.10, without including any other information.
Numerical results should be accurate to 5 decimal places.

# Example
## Input
### Question
in 2010 and 2009, what was the total fair value in billions of ...?
## Output
```python
total_fair_value_2009 = ...
total_fair_value_2010 = ...
# total_fair_value
total_fair_value = total_fair_value_2009 + total_fair_value_2010
print(f"total_fair_value: {total_fair_value:.5f}")
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
