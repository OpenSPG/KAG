import re
import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_expression_builder")
class FinQAExpressionBuildr(PromptABC):
    template_zh = """
# 任务
你是一位财经领域的专家。根据提供的问题和相关信息，编写Python代码以输出问题的答案。

# 注意事项
1. 严格依据输入内容：不得进行任何假设或添加额外信息。
2. 答案只允许为数字或'yes/no'，数字需要精确到小数点后5位。
3. 使用print输出答案时，应尽量附带完整的描述信息，以明确答案的含义。
4. 如果根据提供的信息无法得出答案，print输出：`I don't know.`
5. Python版本为3.10。

# 可参考的解题思路
```
$examples
```

# 输出格式
输出你的思考过程，最后给出python代码，使用```python ```包裹你的代码。

# 例子
## Input
### Question
what was the difference in percentage cumulative total shareholder return on A common stock versus the s&p 500 index for the five year period ended 2017?
## Output
信息中提到`the graph assumes investments of $ 100 on december 31 , 2012 in our common stock`，表中给出了之后几年这$100的投资收益。
其他思考过程...略
```python
masco_2012 = 100
masco_2017 = 318.46
sp500_2012 = 100
sp500_2017 = 206.49
difference_in_percentage = ((masco_2017 - masco_2012) / masco_2012) - ((sp500_2017 - sp500_2012) / sp500_2012)
print(f"the difference in percentage cumulative total shareholder return：{difference_in_percentage:.5f}")
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
You are an expert in the financial field. Based on the given question and relevant information, write Python code to output the answer to the question.

# Notes
1. Strictly adhere to the input: do not make any assumptions or add extra information.
2. The answer should only be a number or 'yes/no'. Numbers need to be precise to five decimal places.
3. When using print to output the answer, ensure the description is as complete as possible to make the answer clear.
4. If the answer cannot be determined based on the given information, print: I don't know.
5. Use Python version 3.10.

# Possible problem-solving strategies for reference
```
$examples
```

# Output Format
Output your reasoning process and provide Python code wrapped in ```python ```.

# Example
## Input
### Question
What was the difference in percentage cumulative total shareholder return on A common stock versus the S&P 500 Index for the five-year period ended 2017?
## Output
Relevant information states: the graph assumes investments of $100 on December 31, 2012, in our common stock, and the table detailed the returns on this $100 investment over the following years.
Other thought processes... omitted
```python
masco_2012 = 100
masco_2017 = 318.46
sp500_2012 = 100
sp500_2017 = 206.49
difference_in_percentage = ((masco_2017 - masco_2012) / masco_2012) - ((sp500_2017 - sp500_2012) / sp500_2012)
print(f"The difference in percentage cumulative total shareholder return is: {difference_in_percentage:.5f}")
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
        pattern = r"```python(.*?)```"
        code = re.search(pattern, response, re.DOTALL)
        code = code.group(1).strip()
        return code
