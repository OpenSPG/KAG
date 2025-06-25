import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_question_classify")
class FinQAQuestionClassify(PromptABC):
    template_zh = """
# 任务
你是一个财经领域专家，你的任务是给问题打上最合适的两到三个标签。

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
输出内容包含以下案例格式。
```
问题分类标签: 平均值, 财务报表分析
```

# 输入
$question

# 你的输出
""".strip()

    template_en = """
# Task
You are a financial expert, and your task is to assign the most appropriate two to three labels to the question.

# Problem Classification Tags
["Percentage and Proportion", "Average", "Total Sum", "Change Amount", "Maximum and Minimum", "Conditional Assumptions Predictions and Inferences", "Time Series", "Changes Within the Year", "Year-End (December 31)", "Fiscal Year", "Financial Statement Analysis", "Taxation and Accounting", "Investments and Stocks", "Debt and Financing", "Corporate Mergers and Restructuring", "Shareholder Equity and Dividends", "Risk Management and Hedging", "Lease Costs"]
Explanation:
- Percentage and Proportion: Questions typically include phrases like "percentage of," "ratio of," "portion of," "percentage change," or "growth rate."
- Conditional Assumptions Predictions and Inferences: Involves deriving potential outcomes based on certain hypothetical conditions.
- Time Series: Problems that deal with specific time periods or ranges of time.
- Year-End (December 31): Questions that involve December 31.
- Changes Within the Year: Questions addressing changes in data over the course of a single year.
- Fiscal Year: Some companies' fiscal years differ from the calendar year, and this distinction may be important.

# Output Format
The output should follow the example format below.
```
Question Classification Labels: Average, Financial Statement Analysis
```

# Input
$question

# Your Output
""".strip()

    @property
    def template_variables(self) -> List[str]:
        return ["question"]

    def parse_response(self, response: str, **kwargs):
        return self.parse_output_format(response)

    def parse_output_format(self, output):
        # 检查输入是否为空或格式不正确
        if not output or "Question Classification Labels:" not in output:
            return []

        # 提取冒号后的内容
        labels_part = output.split("Question Classification Labels:", 1)[1].strip()
        labels_part = labels_part.strip("`\n")

        # 按逗号分割并去除多余空格
        labels = [label.strip() for label in labels_part.split(",")]

        return labels
