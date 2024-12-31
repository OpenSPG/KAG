import logging
import json
from typing import List

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)

from kag.common.base.prompt_op import PromptOp


class LogicFormPlanPrompt(PromptOp):
    template_zh = """
{
  "task": "拆解子问题",
  "instruction": [
    "找出解决问题的核心关键步骤，总结为子问题。",
    "参考函数的能力，将子问题分配给合适的函数进行处理。",
    "参考failed_cases中失败的尝试，其中已回答的子问题不要修改，无法回答的子问题，必须改变思路尝试其他拆解方式，生成新的子问题！"
  ],
  "pay_attention": [
    "你的数学计算能力能力很差，必须使用PythonCoder对数学计算和数值比较问题进行求解。",
    "子问题描述信息要完整，不要遗漏任何关键字，语义要清晰，利于理解。"
  ],
  "output_format": [
    "输出json格式，output给出子问题列表",
    "每个子问题包含sub_question和process_function"
  ],
  "functions": [
    {
      "functionName": "Retrieval",
      "description": "包含一个知识库，根据给出的检索条件(自然语言)，返回检索结果。",
      "pay_attention": [
        "进行子项目召回时，为了保证数据完整性，子问题格式为：***的所有子项",
        "Retrieval的问题必须是具体明确的；不合格的问题：查找财务报表。具体明确的问题：查找2024年全年的净利润值。"
      ],
      "knowledge_base_content": "$kg_content",
      "examples": [
        {
          "knowledge_base_content": "中芯国际2024第3季度财务报表",
          "input": "从资产负债信息中召回流动资产的所有子项",
          "output": "| 项目             | 2024年9月30日 | 2023年12月31日 |\n|------------------|---------------|----------------|\n| 流动资产：       |               |                |\n| 货币资金         | 29,878,544    | 51,235,370     |\n| 结算备付金       | -             | -              |\n| 拆出资金         | -             | -              |\n| 交易性金融资产   | 1,633,233     | 1,520,160      |\n| 衍生金融资产     | 494,335       | 303,397        |\n| 应收票据         | 528,810       | 442,456        |\n| 应收账款         | 3,428,498     | 3,501,291      |\n| 应收款项融资     | -             | -              |\n| 预付款项         | 552,591       | 751,860        |\n| 应收保费         | -             | -              |\n| 应收分保账款     | -             | -              |\n| 应收分保合同准备金 | -           | -              |\n| 其他应收款       | 230,987       | 160,063        |\n| 其中：应收利息   | -             | -              |\n| 应收股利         | -             | -              |\n| 买入返售金融资产 | -             | -              |\n| 存货             | 20,168,932    | 19,377,706     |\n| 其中：数据资源   | -             | -              |\n| 合同资产         | -             | -              |\n| 持有待售资产     | 154,434       | 156,033        |\n| 一年内到期的非流动资产 | 17,834,516 | 15,125,314  |\n| 其他流动资产     | 2,392,787     | 4,000,122      |\n| 流动资产合计     | 77,297,667    | 96,573,772     |"
        }
      ]
    },
    {
      "functionName": "PythonCoder",
      "description": "对给出的问题，编写python代码求解。",
      "pay_attention": "只使用python基础库",
      "examples": [
        {
          "input": "9.8和9.11哪个大？",
          "internal_processing_logic": "编写python代码```python\nanswer=max(9.8, 9.11)\nprint(answer)```, 调用执行器获得结果",
          "output": "9.8"
        },
        {
          "input": "今天星期几？",
          "internal_processing_logic": "```python\nimport datetime\n\n# 获取当前日期\ntoday = datetime.datetime.now()\n\n# 将日期格式化为星期几，%A会给出完整的星期名称\nday_of_week = today.strftime(\"%A\")\n\n# 打印结果\nprint(\"今天是:\", day_of_week)\n```",
          "output": "例子中无法给出答案，取决于具体的运行时间"
        }
      ]
    }
  ],
  "examples": [
    {
      "input": "如果游戏收入按照目前的速度增长，2020年的游戏收入是多少美元？",
      "output": [
        {
          "sub_question": "查找2018年和2019年游戏收入，按照美元计算",
          "process_function": "Retrieval"
        },
        {
          "sub_question": "根据2018年和2019年游戏收入，计算2019年游戏收入增长率；再根据增长率，计算2020年游戏收入",
          "process_function": "PythonCoder"
        }
      ]
    },
    {
      "input": "471乘以473等于多少？",
      "output": [
        {
          "sub_question": "计算471乘以473的结果",
          "process_function": "PythonCoder"
        }
      ]
    },
    {
      "input": "阿里巴巴财报中最新的资产负债信息中流动资产最高的子项是哪个？其占流动资产的比例是多少？",
      "output": [
        {
          "sub_question": "召回阿里巴巴最新的资产负债信息中流动资产总值",
          "process_function": "Retrieval"
        },
        {
          "sub_question": "查询阿里巴巴最新的资产负债信息中所有流动资产详情",
          "process_function": "Retrieval"
        },
        {
          "sub_question": "根据召回的阿里巴巴流动资产详情，计算最高的子项是哪个？并计算最高子项占总流动资产的比例是多少？",
          "process_function": "PythonCoder"
        }
      ]
    }
  ],
  "input": "$input",
  "failed_cases": "$history"
}
"""
    template_en = template_zh

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["input", "kg_content", "history"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        return rsp
