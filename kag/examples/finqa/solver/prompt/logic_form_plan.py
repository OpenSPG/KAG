import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("table_finqa_logic_form_plan")
class LogicFormPlanPrompt(PromptABC):

    template_zh = """
{
  "task": "你的任务是根据输入的问题及其上下文信息，生成尽可能多的子问题，以解决给出的问题。",
  "instruction": [
    "子问题要求尽量多样，避免重复和类似。",
    "确保子问题包含完整的信息，避免使用代词。",
    "将子问题归类到function中的一项上，并按照格式要求输出。",
    "如果给出的信息可以直接得到答案，输出'The context is sufficient to answer the question.'"
  ],
  "function": [
    {
      "function_declaration": "Retrieval(s=s_alias:entity_type[`entity_name`], p=p_alias:edge_type, o=o_alias:entity_type[`entity_name`])",
      "description": "根据spo检索信息，s、p、o不能在同一表达式中反复多次出现。"
    },
    {
      "function_declaration": "Math(content=[], target=`XXX`)->math_alias",
      "description": "执行计算，该算子包含数值计算或排序计数等集合操作。content为空。target为计算的目标，通常是当前子问题。math_alias为变量名，表示其计算结果，可在后续动作中被引用。"
    }
  ],
  "examples": [
    {
      "input": {
        "question": "美国运通的平均每笔交易支付金额是多少？",
        "context": []
      },
      "output": [
        {
          "subquestion": "美国运通的支付总金额是多少？",
          "function": "Retrieval(s=s1:Company[`american express`], p=p1:totalPaymentVolume, o=o1)"
        },
        {
          "subquestion": "美国运通的交易总数量是多少？",
          "function": "Retrieval(s=s1:Company[`american express`], p=p1:numberOfTransactions, o=o1)"
        },
        "其他子问题"
      ]
    },
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
          "function": "Math(content=[`支付总金额是637十亿美元，交易总笔数是5十亿笔`], target=`计算平均每笔交易支付金额`)"
        }
      ]
    },
    {
      "input": {
        "question": "美国运通的平均每笔交易支付金额是多少？",
        "context": [
          "| company          | payments volume ( billions )   | total volume ( billions )   |   total transactions ( billions ) |   cards ( millions ) |\n| american express | 637                            | 647                         |                               5   |                   86 |",
          "支付总金额是637十亿美元，交易总笔数是5十亿笔，平均每笔交易支付金额是127.4"
        ]
      },
      "output": "The context is sufficient to answer the question."
    }
  ],
  "output_format": "json格式，输出子问题列表，每个子问题给出对应的function表示",
  "real_input": "$input"
}
""".strip()

    template_en = template_zh

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
