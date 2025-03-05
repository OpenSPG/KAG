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

# Instruction
1. 如果给出的信息不足以回答问题，规划下一步的操作为Retrieval类子问题；Retrieval类子问题尽可能切中主题。
2. 如果信息足够回答问题，规划下一步的操作为Math类子问题；Math子问题通过计算模块得到精确答案。
3. 如果Math子问题已经计算得到问题答案，输出：`An explicit answer already exists.`
4. 如果子问题答案存在矛盾，分析原文信息，以原文为准。

# 输出格式
先输出你的思考过程，最后输出下一步操作的类型Retrieval或Math，然后给出子问题列表。
格式例子如下：
```
Retrieval: 
example_retrieval_subquestion_1
example_retrieval_subquestion_2
```

# 例子
## 案例输入
** 你需要回答的问题 **: 美国运通平均每笔交易支付金额是多少？
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
```
Math:
支付总金额是637十亿美元，支付总笔数是5十亿笔。计算平均每笔交易的支付金额。
```

# 真正的输入
** 你需要回答的问题 **: $question
** 已知信息**:
$context
""".strip()

    template_en = """
# Task
You are a financial expert. Based on the provided question and information, plan the next steps.

# Instruction
1. If the provided information is insufficient to answer the question, plan the next step as a Retrieval-type sub-question. Retrieval-type sub-questions should be as focused and relevant to the topic as possible.
2. If the information is sufficient to answer the question, plan the next step as a Math-type sub-question. Math sub-questions are solved using a computation module to obtain precise answers.
3. If the Math sub-question has already been computed to find the problem's answer, output: `An explicit answer already exists.`
4. If contradictions exist in the sub-question answers, analyze the original text, and prioritize the original text as the basis for resolution.

# Output Format
First, explain your thought process. Then output the next step's operation type, either Retrieval or Math, followed by the sub-question list.
The format example is as follows:
```
Retrieval: 
example_retrieval_subquestion_1
example_retrieval_subquestion_2
```

# Example
## Case Input
** The question you need to answer **: What is the average payment amount per transaction for American Express?
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
```
Math:
The total payment volume is $637 billion, and the total number of transactions is 5 billion. Calculate the average payment amount per transaction.
```

# Actual Input
** The question you need to answer **: $question
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
        flag_str = "```"
        start_i = text.find(flag_str)
        end_i = text.rfind(flag_str)
        if start_i == -1 or end_i == -1 or start_i >= end_i:
            return []
        text = text[start_i + len(flag_str) : end_i].strip()
        type_start = 0
        type_end = text.index(":")
        type_str = text[type_start:type_end].strip()
        if type_str.lower() not in ["math", "retrieval"]:
            return []
        if type_str.lower() == "retrieval":
            type_str = "Retrieval(s=s1:EntityType[`s1`],p=p1:p,o=o1)"
        elif type_str.lower() == "math":
            type_str = "Math(content=[], target='')->m"
        subquestions = text[type_end + 1 :].strip()
        subquestions = self.remove_line_numbers(subquestions)
        subquestions = subquestions.splitlines()
        results = []
        for subq in subquestions:
            if type_str.lower() == "math":
                type_str = f"Math(content=[], target='{subq}')->m"
            results.append((subq, type_str))
        return results

    def remove_line_numbers(self, text):
        # 使用正则表达式匹配每行开头的序号
        return re.sub(r"^\d+\.\s*", "", text, flags=re.MULTILINE)