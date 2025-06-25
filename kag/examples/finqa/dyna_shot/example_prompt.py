import re
import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_build_example_prompt")
class FinQABuildExamplePrompt(PromptABC):
    template_zh = """
# 任务
你是一个财经领域专家，你的任务是分析给出的问题及其参考信息。
输出以下信息：
1. 参考给定的分类标签，针对问题选择两到三个最合适的标签。
2. 判断该问题的解题思路是否正确。
3. 解决该问题的计算方法或者公式。注意：变量名要完整详实，能准确理解改变量意义。除常量外，不要出现具体数字。

# 问题分类标签
["百分比和比例", "平均值", "总量合计", "变化量", "最大最小值", "条件假设,预测和推断", "时间序列", "年内变化", "一年最后一天", "财年", "财务报表分析", "税务和会计", "投资和股票", "债务和融资", "企业并购与重组", "股东权益与分红", "风险管理与对冲", "租赁费用"]
说明：
百分比和比例：问题中一般包含percentage of, ratio of, portion of, percentage change, growth rate等
条件假设,预测和推断：基于某些假设条件，要求推导出可能的结果。
时间序列类：问题涉及到某一时段，或时间范围。
年内变化：某个数据在一年内的变化。
一年最后一天：包含12月31日的的问题。
财年：某些公司财年与自然年有差异，需要注意这个差异。

# 输出格式
先输出你的思考过程，格式随意，最后一部分要严格按照格式输出。
以下是一个输出格式的例子：
需要回答的问题是：what was the growth rate of the equity income in drilling fluids joint venture the mi-swaco from 2007 to 2007 for schlumberger
你的思考过程...略
```
<tags>Percentage and Proportion, Time Series, Investments and Stocks</tags>
<correct>yes</correct>
<formula>Growth Rate = (Equity Income in Year 2008 - Equity Income in Year 2007) / Equity Income in Year 2007</formula>
```

# 真正的输入
问题: $question
参考信息: 
```
$info
```
参考的计算过程: $process

# 你的输出
""".strip()

    template_en = """
# Task
You are an expert in the field of finance. Your task is to analyze the given question and its reference information.
Provide the following information:
1. Based on the given classification labels, select two to three most appropriate tags for the question.
2. Assess whether the proposed approach to solving the problem is correct.
3. The calculation method or formula to solve the problem. Note: Variable names must be complete and detailed, allowing for a clear understanding of their meanings. No specific numbers should appear except for constants.

# Question Classification Labels
["Percentage and Proportion", "Average", "Total Sum", "Change Amount", "Maximum and Minimum", "Conditional Assumptions Predictions and Inferences", "Time Series", "Changes Within the Year", "Year-End (December 31)", "Fiscal Year", "Financial Statement Analysis", "Taxation and Accounting", "Investments and Stocks", "Debt and Financing", "Corporate Mergers and Restructuring", "Shareholder Equity and Dividends", "Risk Management and Hedging", "Lease Costs"]
Explanation:
- Percentage and Proportion: Questions typically include phrases like "percentage of," "ratio of," "portion of," "percentage change," or "growth rate."
- Conditional Assumptions Predictions and Inferences: Involves deriving potential outcomes based on certain hypothetical conditions.
- Time Series: Problems that deal with specific time periods or ranges of time.
- Year-End (December 31): Questions that involve December 31.
- Changes Within the Year: Questions addressing changes in data over the course of a single year.
- Fiscal Year: Some companies' fiscal years differ from the calendar year, and this distinction may be important.

# Output Format
First, output your thought process, the format of which can vary. The final section must strictly follow the specified format.
Here is an example of the output format:
The question to be answered is: what was the growth rate of the equity income in the drilling fluids joint venture the mi-swaco from 2007 to 2008 for Schlumberger?
Your thought process... omitted
```
<tags>Percentage and Proportion, Time Series, Investments and Stocks</tags>
<correct>yes</correct>
<formula>Growth Rate = (Equity Income in Year 2008 - Equity Income in Year 2007) / Equity Income in Year 2007</formula>
```

# Actual Input
Question: $question
Reference Information:
```
$info
```
Reference Calculation Process: $process

# Your Output
""".strip()

    @property
    def template_variables(self) -> List[str]:
        return ["question", "info", "process"]

    def parse_response(self, response: str, **kwargs):
        return self.parse_output(response)

    def parse_output(self, output):
        # Define the regex patterns for tags, correctness, and formula
        tags_pattern = r"<tags>(.*?)</tags>"
        correct_pattern = r"<correct>(.*?)</correct>"
        formula_pattern = r"<formula>(.*?)</formula>"

        # Extract data using regex
        tags_match = re.search(tags_pattern, output, re.DOTALL)
        correct_match = re.search(correct_pattern, output, re.DOTALL)
        formula_match = re.search(formula_pattern, output, re.DOTALL)

        # Retrieve and strip data from matches
        tags = tags_match.group(1).strip() if tags_match else None
        correct = correct_match.group(1).strip() if correct_match else None
        formula = formula_match.group(1).strip() if formula_match else None

        return tags, correct, formula
