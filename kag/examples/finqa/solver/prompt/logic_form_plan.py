import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_finqa_logic_form_plan")
class LogicFormPlanPrompt(PromptABC):

    template_zh = """
# 任务
你拥有丰富的财经领域知识，针对给出的问题和信息，规划下一步操作。
问题答案只可能是一个数字或者yes/or。

# 要求
1. 如果给出的信息不足以回答问题，规划下一步的操作为Retrieval类子问题。召回解答问题需要的信息。
2. 如果信息足够回答问题，注意观察信息中是否有Math类问题及答案。如果Math类问题已经给出了问题的最终答案，输出：`An explicit answer already exists.`
3. 如果没有Math类子问题，或者Math没有回答最终问题，规划下一步的操作为Math类子问题；使用Math类子问题调用计算模块得到答案。

# 输出格式
先输出你的思考过程，最后按照如下格式，将规划输出到<plan></plan>标签中。子问题不需要序号，按行分割。
<plan>
Retrieval/Math:
example_retrieval_or_math_subquestion_1
example_retrieval_or_math_subquestion_2
</plan>

# 例子
## 案例输入
** 你需要规划的问题 **: 美国运通平均每笔交易支付金额是多少？
** 已知信息**:
SubQuestion1: 美国运通的支付总金额是多少？ by:retrival
Answer1: 美国运通的支付总金额是637十亿美元。
Document1:
| company          | payments volume ( billions )   | total volume ( billions )   |   total transactions ( billions ) |   cards ( millions ) |
| american express | 637                            | 647                         |                               5   |                   86 |

## 案例输出
求解的问题是：美国运通平均每笔交易支付金额是多少？
通过问题1的答案，我们可以得到美国运通的支付总金额是637十亿美元。同时从Document1可以获得美国运通总支付次数是5十亿次。
因此已经具有足够的信息计算平均每笔交易支付金额。
规划下一步操作为Math类子问题，已经具备回答问题的信息，因此math子问题给出数据，然后引用问题原文即可。
<plan>
Math:
美国运通的支付总金额是637十亿美元，总交易次数是5十亿次；美国运通平均每笔交易支付金额是多少？
</plan>

# 可供参考的解题思路
```
$examples
```

# 真正的输入
** 你需要规划的问题 **: $question
** 已知信息**:
```
$context
```
""".strip()

    template_en = """
# Task
You have extensive knowledge in the field of finance. Based on the given question and information, plan the next step of action.
The answer to the question can only be a number or yes/no.

# Instruction
1. If the provided information is insufficient to answer the question, plan the next step as a Retrieval-type subtask. Retrieve the information required to answer the question.
2. If the information is sufficient to answer the question, carefully check if there is a Math-type problem and its answer within the information. If the Math-type problem already provides the final answer to the question, output: `An explicit answer already exists.`
3. If there is no Math-type subtask, or if the Math-type subtask does not provide the final answer, plan the next step as a Math-type subtask. Use the Math-type subtask to invoke a calculation module to determine the answer.

# Output Format
First, output your thought process, and finally, according to the following format, output the plan within the <plan></plan> tags. Sub-questions do not need numbering and should be separated by line breaks.
<plan>
Retrieval/Math:
example_retrieval_or_math_subquestion_1
example_retrieval_or_math_subquestion_2
</plan>

# Example
## Case Input
** The question you need to plan for **: What is the average payment amount per transaction for American Express?
** Known information **:
```
SubQuestion1: What is the total payment volume for American Express? by:retrieval
Answer1: The total payment volume for American Express is $637 billion.
Document1:
| company          | payments volume ( billions )   | total volume ( billions )   |   total transactions ( billions ) |   cards ( millions ) |
| american express | 637                            | 647                         |                               5   |                   86 |
```

## Case Output
The problem to solve is: What is the average payment amount per transaction for American Express?
From the answer to SubQuestion1, we know that the total payment volume for American Express is $637 billion. Additionally, Document1 provides the total number of transactions, which is 5 billion.
Therefore, we already have sufficient information to calculate the average payment amount per transaction.
The next step in the plan is a Math subproblem. Since we already have all the necessary information to answer the question, the math subproblem will provide the data, and then reference the original question.
<plan>
Math:
The total payment amount for American Express is $637 billion, and the total number of transactions is 5 billion. What is the average payment amount per transaction for American Express?
</plan>

# Reference Problem-Solving Approach
```
$examples
```

# Actual Input
** The question you need to plan for **: $question
** Known Information **:
```
$context
```
""".strip()

    @property
    def template_variables(self) -> List[str]:
        return ["question", "context", "examples"]

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
