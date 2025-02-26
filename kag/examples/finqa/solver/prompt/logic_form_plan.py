import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_finqa_logic_form_plan")
class LogicFormPlanPrompt(PromptABC):

    template_zh = """
# Task
根据问题及上下文信息，生成尽可能多样且无重复的子问题，帮助解答原问题。

# Instruction
1. 子问题应尽量多样，避免重复或类似。
2. 每个子问题需归类到 `functions` 中的一项，并按指定格式输出 `function`。
3. 上下文信息不足时生成Retrieval类子问题，上下文信息充足时生成Math子问题以解决最终的问题。
4. 如果子问题中已有明确的答案回答最终问题(Math计算的结果)，输出：`An explicit answer already exists.`

# Functions
## 1. **Retrieval**
格式: Retrieval(s=s_alias:entity_type[`entity_name`], p=p_alias:edge_type, o=o_alias:entity_type[`entity_name`])
注释: 检索信息，基于 SPO（主谓宾）结构。不要在同一表达式中多次重复 `s`、`p` 或 `o`。

## 2. **Math**
格式: Math(content=[], target=`XXX`)->math_alias
注释: 执行数值计算，content为上下文信息，target为计算目标。

# Output Format
输出纯文本，先输出你的思考过程，最后给出Subquestion和Function的配对，一行一个，配对之间使用|||分割。
格式如下：```
Subquestion: example_subquestion1|||Function: example_function1
Subquestion: example_subquestion2|||Function: example_function2
```

# Examples
## Example Input
Question: 美国运通的平均每笔交易支付金额是多少？
Context:
SubQuestion1: 美国运通的交易总数量是多少？ by:retrival
Answer1:
| company          | payments volume ( billions )   | total volume ( billions )   |   total transactions ( billions ) |   cards ( millions ) |
| american express | 637                            | 647                         |                               5   |                   86 |

## Example Output
求解的问题是：美国运通的平均每笔交易支付金额是多少？
通过问题1的答案，我们可以得到美国运通的交易总数量是5十亿笔。同时可以获得美国运通的支付总金额是637十亿美元。
因此已经具有足够的信息计算平均每笔交易支付金额。
子问题列表如下:
Subquestion: 支付总金额是637十亿美元，支付总笔数是5十亿笔。计算平均每笔交易的支付金额？|||Function: Math(content=[], target=`计算平均每笔交易支付金额`)

# Real Input
Question: $question
Context:
$context
""".strip()

    template_en = """
# Task
Generate as many diverse and non-redundant subquestions as possible to help answer the main question based on the given question and context.

# Instruction
1. The subquestions should be as diverse as possible and avoid repetition or being overly similar.
2. Each subquestion should be categorized under one of the `functions` and formatted accordingly.
3. When contextual information is insufficient, generate sub-questions of the Retrieval type; when contextual information is sufficient, generate sub-questions of the Math type to solve the final problem.
4. If the sub-problem list already contains a clear answer to the final question (the result of the math calculation), output: `An explicit answer already exists.`

# Functions
## 1. **Retrieval**
Format: Retrieval(s=s_alias:entity_type[`entity_name`], p=p_alias:edge_type, o=o_alias:entity_type[`entity_name`])
Note: Retrieve information based on SPO (subject-predicate-object) structure. Do not repeat `s`, `p`, or `o` in the same expression.

## 2. **Math**
Format: Math(content=[], target=`XXX`)->math_alias
Note: Perform numerical calculations. `content` refers to contextual information, and `target` specifies the calculation goal.

# Output Format
Output plain text. Start by explaining your reasoning, then provide subquestions paired with their respective functions. List one per line, separating each pair with `|||`.
Format as follows:
```
Subquestion: example_subquestion1|||Function: example_function1
Subquestion: example_subquestion2|||Function: example_function2
```

# Examples
## Example Input
Question: What is the average amount paid per American Express transaction?
Context:
SubQuestion1: What is the total number of American Express transactions? by:retrieval
Answer1:
| company          | payments volume ( billions )   | total volume ( billions )   |   total transactions ( billions ) |   cards ( millions ) |
| american express | 637                            | 647                         |                               5   |                   86 |

## Example Output
The problem to solve is: What is the average amount paid per American Express transaction?
Based on the answer to Subquestion1, we know the total number of American Express transactions is 5 billion. Additionally, we can see that the total payment amount is $637 billion.
Thus, we have sufficient information to calculate the average amount paid per transaction.
The subquestions and functions are as follows:
Subquestion: The total payment amount is $637 billion, and the total transaction count is 5 billion. What is the average payment amount per transaction?|||Function: Math(content=[], target=`Calculate the average payment amount per transaction`)

# Real Input
Question: $question
Context:
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
        lines = text.splitlines()
        results = []
        for line in lines:
            try:
                line = line.strip()
                if line.startswith("Subquestion:") and "|||Function:" in line:
                    subq_start = len("Subquestion: ")
                    func_start = line.index("|||Function: ") + len("|||Function: ")
                    subq = line[subq_start : line.index("|||Function: ")].strip()
                    func = line[func_start:].strip()
                    results.append((subq, func))
            except:
                continue
        return results
