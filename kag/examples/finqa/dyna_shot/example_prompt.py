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
1. 该问题的解题思路是否正确。
2. 参考给定的分类标签，针对问题选择两到三个最合适的标签。
3. 将解题过程总结成一个优质的案例，供他人参考。

# 问题分类标签
["百分比和比例", "平均值", "总量合计", "变化量", "最大最小值", "条件假设,预测和推断", "时间序列", "一年最后一天", "财务报表分析", "税务和会计", "投资和股票", "债务和融资", "企业并购与重组", "股东权益与分红", "风险管理与对冲", "租赁费用"]
说明：
百分比和比例： 问题中一般包含percentage of, ratio of, portion of, percentage change, growth rate等
条件假设,预测和推断： 基于某些假设条件，要求推导出可能的结果。
时间序列类：问题涉及到某一时段，或时间范围。
一年最后一天： 包含12月31日的的问题。

# 举例
## 输入
问题: what is the difference between the payments for revenue from clients and the actual revenue recorded , ( in millions ) ?
参考信息:
table row 3 shows ( amounts in millions ) the accrued warranty of 2013 is 17.0 ; the accrued warranty of 2012 is 18.9 ;
table row 4 shows ( amounts in millions ) the deferred subscription revenue of 2013 is 26.6 ; the deferred subscription revenue of 2012 is 24.8 ;
计算过程: subtract(26.6, 24.8)

## 输出
思考过程：根据参考信息，表格中提供了“递延订阅收入（Deferred Subscription Revenue）”的数据，这通常是用来衡量客户付款与实际收入确认之间差异的关键指标。递延订阅收入的变化反映了客户付款与实际确认收入之间的差异。如果递延订阅收入增加，说明客户付款多于实际确认的收入；如果减少，则说明实际确认的收入多于客户付款。
解题思路: 正确
问题分类标签: 变化量, 财务报表分析
供参考案例:
<example>
问题: what is the difference between the payments for revenue from clients and the actual revenue recorded , ( in millions ) ?
参考信息: ( amounts in millions ) the deferred subscription revenue of 2013 is 26.6 ; the deferred subscription revenue of 2012 is 24.8 ;
数据提取: 获取递延订阅收入，这通常是用来衡量客户付款与实际收入确认之间差异的关键指标。
计算方法: 计算递延订阅收入的变化量：用2013年的值减去2012年的值。变化量 = 2013年递延订阅收入 - 2012年递延订阅收入
</example>

# 输出格式
先输出你的思考过程，格式随意。最后一部分要严格按照以下格式输出：
```
解题思路: [正确还是错误]
问题分类标签: [多个标签, 使用逗号分隔]
供参考案例: [使用<example></example>标签]
```

# 真正的输入
问题: $question
参考信息: $info
计算过程: $process

# 你的输出
""".strip()

    template_en = """
# Task
You are a financial expert, and your task is to analyze the given question and its reference information.
Output the following information:
1. Whether the reasoning process for solving the problem is correct.
2. Referring to the given classification tags, select two to three most appropriate tags for the question. 
3. Summarize the solution process into a high-quality case study for others to reference.

# Problem Classification Tags
["Percentage and Proportion", "Average", "Total Sum", "Change Amount", "Maximum and Minimum Values", "Conditional Assumptions Predictions and Inferences", "Time Series", "Last Day of the Year", "Financial Statement Analysis", "Tax and Accounting", "Investment and Stocks", "Debt and Financing", "Mergers and Acquisitions", "Shareholder Equity and Dividends", "Risk Management and Hedging", "Lease Expenses"]

Explanation:
- Percentage and Proportion: Questions generally include terms like percentage of, ratio of, portion of, percentage change, growth rate, etc.
- Conditional Assumptions, Predictions, and Inferences: Results are derived based on certain assumptions.
- Time Series: Questions involve a specific time period or range.
- Last Day of the Year: Questions that include December 31st.

# Example
## Input
Question: What is the difference between the payments for revenue from clients and the actual revenue recorded, (in millions)?
Reference Information:
Row 3 of the table shows (amounts in millions) the accrued warranty for 2013 is 17.0; the accrued warranty for 2012 is 18.9.
Row 4 of the table shows (amounts in millions) the deferred subscription revenue for 2013 is 26.6; the deferred subscription revenue for 2012 is 24.8.
Calculation Process: Subtract(26.6, 24.8)

## Output
Thought Process: According to the reference information, the table provides data on "deferred subscription revenue," which is typically a key indicator used to measure the difference between client payments and actual revenue recognition. Changes in deferred subscription revenue reflect the difference between client payments and actual recognized revenue. An increase in deferred subscription revenue indicates that client payments exceed actual recognized revenue, while a decrease suggests the opposite.
Solution Approach: Correct
Problem Classification Tags: Change Amount, Financial Statement Analysis
Case Study for Reference:
<example>
Question: What is the difference between the payments for revenue from clients and the actual revenue recorded, (in millions)?
Reference Information: (Amounts in millions) The deferred subscription revenue for 2013 is 26.6; the deferred subscription revenue for 2012 is 24.8.
Data Extraction: Obtain the deferred subscription revenue, which is typically a key indicator used to measure the difference between client payments and actual revenue recognition.
Calculation Method: Calculate the change in deferred subscription revenue: subtract the 2012 value from the 2013 value. Change Amount = Deferred Subscription Revenue in 2013 - Deferred Subscription Revenue in 2012.
</example>

# Output Format
First, provide your thought process in any format. The final section must strictly follow this format:
```
Solution Approach: [Correct or Incorrect]
Problem Classification Tags: [Multiple tags, separated by commas]
Case Study for Reference: [Use <example></example> tags]
```

# Real Input
Question: $question
Reference Information: $info
Calculation Process: $process

# Your Output
""".strip()

    @property
    def template_variables(self) -> List[str]:
        return ["question", "info", "process"]

    def parse_response(self, response: str, **kwargs):
        return self.parse_model_output(response)

    def parse_model_output(self, output):
        # 提取解题思路
        if self.language == "zh":
            solution_match = re.search(r"解题思路:\s*([^\n]+)", output)
        else:
            solution_match = re.search(r"Solution Approach:\s*([^\n]+)", output)
        solution = (
            solution_match.group(1).strip() if solution_match else "未找到解题思路"
        )

        # 提取问题分类标签
        if self.language == "zh":
            tags_match = re.search(r"问题分类标签:\s*([^\n]+)", output)
        else:
            tags_match = re.search(r"Problem Classification Tags:\s*([^\n]+)", output)
        tags = (
            [tag.strip() for tag in tags_match.group(1).split(",")]
            if tags_match
            else []
        )

        # 提取供参考案例
        example_match = re.search(r"<example>(.*?)</example>", output, re.DOTALL)
        example = (
            example_match.group(1).strip() if example_match else "未找到供参考案例"
        )

        return solution, tags, example
