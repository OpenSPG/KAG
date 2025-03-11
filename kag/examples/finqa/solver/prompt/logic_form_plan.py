import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_finqa_logic_form_plan")
class LogicFormPlanPrompt(PromptABC):

    template_zh = """
# Task
你是一个财务专家，针对给出的问题和信息，规划下一步操作。
问题的最终答案是一个数字或者yes/no。

# Instruction
1. 如果给出的信息不足以回答问题，规划下一步的操作为Retrieval类子问题；Retrieval类子问题尽可能多样，不重复，从不同角度获取数据。
2. 如果信息足够回答问题，规划下一步的操作为Math类子问题；Math子问题通过编写Python代码并执行得到结果，可解决复杂计算问题。
3. 必须使用Math计算最终答案，如果已有Math类子问题给出来明确的最终答案，输出：`An explicit answer already exists.`

# 输出格式
先输出你的思考过程，最后输出下一步操作的类型Retrieval或Math，然后给出子问题列表。
格式例子如下：
<plan>
Retrieval:
example_retrieval_subquestion_1
example_retrieval_subquestion_2
</plan>

# 例子
## 案例输入
** 你需要规划的问题 **: 美国运通平均每笔交易支付金额是多少？
** 已知信息**:
SubQuestion1: 美国运通的支付总金额是多少？ by:retrival
Answer1: 美国运通的支付总金额是637十亿美元。
SupportingFacts1:
| company          | payments volume ( billions )   | total volume ( billions )   |   total transactions ( billions ) |   cards ( millions ) |
| american express | 637                            | 647                         |                               5   |                   86 |

## 案例输出
求解的问题是：美国运通平均每笔交易支付金额是多少？
通过问题1的答案，我们可以得到美国运通的支付总金额是637十亿美元。同时从SupportingFacts1可以获得美国运通总支付次数是5十亿次。
因此已经具有足够的信息计算平均每笔交易支付金额。
下一步操作为Math类子问题，子问题列表如下:
<plan>
Math:
支付总金额是637十亿美元，支付总笔数是5十亿笔。计算平均每笔交易的支付金额。
</plan>

# 真正的输入
** 你需要规划的问题 **: $question
** 已知信息**:
$context
""".strip()

    template_en = """
# Task
You are a financial expert tasked with planning the next steps based on the given questions and information.
The final answer to the question is either a number or yes/no.

# Instruction
1. If the provided information is insufficient to answer the question, plan the next step as a Retrieval-type subproblem. Retrieval-type subproblems should be as diverse as possible, avoiding repetition, and should aim to gather data from different angles.
2. If the information is sufficient to answer the question, plan the next step as a Math-type sub-question. Math-type sub-questions should involve writing and executing Python code to solve complex calculations and derive results.
3. The final answer must be calculated using Math. If a Math-type subproblem has already provided an explicit final answer, output: `An explicit answer already exists.`

# Output Format
First, explain your thought process. Then output the next step's operation type, either Retrieval or Math, followed by the sub-question list.
The format example is as follows:
<plan>
Retrieval: 
example_retrieval_subquestion_1
example_retrieval_subquestion_2
</plan>

# Example
## Case Input
** The question you need to plan for **: What is the average payment amount per transaction for American Express?
** Known information **:
SubQuestion1: What is the total payment volume for American Express? by:retrieval
Answer1: The total payment volume for American Express is $637 billion.
SupportingFacts1:
| company          | payments volume ( billions )   | total volume ( billions )   |   total transactions ( billions ) |   cards ( millions ) |
| american express | 637                            | 647                         |                               5   |                   86 |

## Case Output
The problem to solve is: What is the average payment amount per transaction for American Express?
From the answer to SubQuestion1, we know that the total payment volume for American Express is $637 billion. Additionally, SupportingFacts1 provides the total number of transactions, which is 5 billion.
Therefore, we already have sufficient information to calculate the average payment amount per transaction.
The next step is a Math-type sub-question, and the sub-question list is as follows:
<plan>
Math:
The total payment volume is $637 billion, and the total number of transactions is 5 billion. Calculate the average payment amount per transaction.
</plan>

# Actual Input
** The question you need to plan for **: $question
** Known information **:
$context
""".strip()

    @property
    def template_variables(self) -> List[str]:
        return ["question", "context"]

    def parse_response(self, response, **kwargs):
        try:
            logger.debug(f"logic form:{response}")
            response_str = str(response)
            flag = "An explicit answer already exists".lower()
            if flag in response_str.lower():
                return [], []
            q_lsit = self._extract_subquestions_and_functions(response_str)
            sub_querys = []
            logic_forms = []
            for q, f in q_lsit:
                sub_querys.append(q)
                logic_forms.append(f)
            return sub_querys, logic_forms
        except Exception as e:
            logger.warning(f"{response} parse logic form faied {e}", exc_info=True)
            return sub_querys, logic_forms

    def _extract_subquestions_and_functions(self, text: str):
        # 定义正则表达式，匹配 <plan> 和 </plan> 之间的内容
        plan_pattern = r"<plan>(.*?)</plan>"
        match = re.search(plan_pattern, text, re.DOTALL)  # re.DOTALL 允许匹配换行符
        if not match:
            return []
        text = match.group(1).strip()
        type_start = 0
        type_end = text.index(":")
        type_str = text[type_start:type_end].strip()
        if type_str.lower() not in ["math", "retrieval"]:
            return []
        if type_str.lower() == "retrieval":
            type_str = "Retrieval(s=s1:EntityType[`s1`],p=p1:p,o=o1)"
            subquestions = text[type_end + 1 :].strip()
            subquestions = self.remove_line_numbers(subquestions)
            subquestions = subquestions.splitlines()
        elif type_str.lower() == "math":
            type_str = "Math(content=[], target='')->m"
            subquestions = [text[type_end + 1 :].strip()]
        results = []
        for subq in subquestions:
            results.append((subq, type_str))
        return results

    def remove_line_numbers(self, text):
        # 使用正则表达式匹配每行开头的序号
        return re.sub(r"^\d+\.\s*", "", text, flags=re.MULTILINE)
