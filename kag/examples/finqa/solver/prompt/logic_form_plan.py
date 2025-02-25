import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_finqa_logic_form_plan")
class LogicFormPlanPrompt(PromptABC):

    template_zh = """
{
  "task": "根据问题及上下文信息，生成尽可能多样且无重复的子问题，帮助解答原问题。",
  "instruction": [
    "子问题应尽量多样，避免重复或类似。",
    "每个子问题需归类到functions中的一项，并按指定格式输出function。",
    "如果上下文已能直接回答问题，输出：'The context is sufficient to answer the question.'"
  ],
  "functions": [
    {
      "function_declaration": "Retrieval(s=s_alias:entity_type[`entity_name`], p=p_alias:edge_type, o=o_alias:entity_type[`entity_name`])",
      "description": "根据spo检索信息，s、p、o不能在同一表达式中反复多次出现。"
    },
    {
      "function_declaration": "Math(content=[], target=`XXX`)->math_alias",
      "description": "执行计算，该算子包含数值计算或排序计数等集合操作。content为空。target为计算的目标，通常是当前子问题。math_alias为变量名，表示其计算结果。"
    }
  ],
  "examples": [
    {
      "input": {
        "question": "美国运通的平均每笔交易支付金额是多少？",
        "context": [
          "| company          | payments volume ( billions )   | total volume ( billions )   |   total transactions ( billions ) |   cards ( millions ) |\n| american express | 637                            | 647                         |                               5   |                   86 |"
        ]
      },
      "output": [
        {
          "subquestion": "支付总金额是637十亿美元，支付总笔数是5十亿笔。计算平均每笔交易的支付金额？",
          "function": "Math(content=[], target=`计算平均每笔交易支付金额`)"
        },
        {
          "subquestion": "美国运通的交易总数量是多少？",
          "function": "Retrieval(s=s1:Company[`american express`], p=p1:numberOfTransactions, o=o1)"
        },
        "more subquestions"
      ]
    }
  ],
  "output_format": "json格式，输出子问题列表，每个子问题给出对应的function表示",
  "real_input": "$input"
}
""".strip()

    template_en = """
{
  "task": "Based on the given question and its context, generate as many diverse and non-repetitive sub-questions as possible to help address the original question.",
  "instruction": [
    "Sub-questions should be as diverse as possible, avoiding repetition or similarity.",
    "Each sub-question must be categorized under one of the items in "functions" and output according to the specified format.",
    "If the context is sufficient to answer the question, output: 'The context is sufficient to answer the question.'"
  ],
  "functions": [
    {
      "function_declaration": "Retrieval(s=s_alias:entity_type[`entity_name`], p=p_alias:edge_type, o=o_alias:entity_type[`entity_name`])",
      "description": "Retrieve information based on an SPO (subject-predicate-object) structure. Do not repeat s, p, or o multiple times within the same expression."
    },
    {
      "function_declaration": "Math(content=[], target=`XXX`)->math_alias",
      "description": "Perform calculations, including numeric computations or operations like sorting, counting, etc. 'content' is left empty, while 'target' specifies the goal of the calculation, typically the current sub-question. The result is stored in 'math_alias'."
    }
  ],
  "examples": [
    {
      "input": {
        "question": "What is the average payment amount per transaction for American Express?",
        "context": [
          "| company          | payments volume ( billions )   | total volume ( billions )   |   total transactions ( billions ) |   cards ( millions ) |\n| american express | 637                            | 647                         |                               5   |                   86 |"
        ]
      },
      "output": [
        {
          "subquestion": "The payment volume is $637 billion, and the total number of transactions is 5 billion. Calculate the average payment amount per transaction.",
          "function": "Math(content=[], target=`Calculate the average payment amount per transaction`)"
        },
        {
          "subquestion": "What is the total transaction count for American Express?",
          "function": "Retrieval(s=s1:Company[`american express`], p=p1:numberOfTransactions, o=o1)"
        },
        "more subquestions"
      ]
    }
  ],
  "output_format": "Output a list of sub-questions in JSON format, with each sub-question paired with its corresponding function representation.",
  "real_input": "$input"
}
""".strip()

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response, **kwargs):
        try:
            logger.debug(f"logic form:{response}")
            if isinstance(response, str):
                flag = "The context is sufficient to answer the question.".lower()
                if flag in response.lower():
                    return [], []
            sub_querys = []
            logic_forms = []
            if isinstance(response, list):
                for subq in response:
                    sub_querys.append(subq["subquestion"])
                    logic_forms.append(subq["function"])
            elif isinstance(response, str):
                return sub_querys, logic_forms
            return sub_querys, logic_forms
        except Exception as e:
            logger.warning(f"{response} parse logic form faied {e}", exc_info=True)
            return [], []
