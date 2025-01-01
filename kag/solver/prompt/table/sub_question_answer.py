import re
from string import Template
from typing import List
import logging

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class RespGenerator(PromptOp):
    template_zh = """{
    "指令": "你是一个信息分析专家，根据给定的信息和领域知识进行分析，并且按照指定格式输出分析内容",
    "要求": [
        "基于给定的信息进行分析",
        ”json格式输出，包含两个字段‘can_answer’和‘analysis’, can_answer为'yes' 或者 'no'，表示是否能根据给定信息进行回答； analysis为输出的分析结果“
        "答案要包含上下文信息，使得没有任何背景的人也能理解。",
        "不要尝试进行数值单位换算，忠实的按照原文输出数值，带上单位和变量"
    ],
    "示例1": {
        "问题": "张三和李四谁年纪大",
        "领域知识": "谁生日年份越小，谁的年纪越大"
        "信息": [
            "张三出生于1990年",
            "李四出生于1991年",
        ],
        "输出": {
            "can_answer": "yes",
            "analysis": "张三年纪比李四大，，因为根据检索信息张三出生于1990年，而李四出生于1991年，所以张三年纪比李四大"
        }
    },
    "示例2": {
        "问题": "阿里巴巴的主要业务是什么",
        "领域知识": "",
        "信息": [
            "阿里巴巴是一家世界级规模的公司",
            "阿里巴巴旗下淘宝天猫是世界上有名的电商平台"
        ],
        "输出": {
            "can_answer": "no",
            "analysis": "根据检索信息无法回答问题，但是可以知道阿里巴巴旗下淘宝天猫是电商平台，以电商为主"
        }
    },
    "示例3": {
        "问题": "A股市场上有多少支股票",
        "领域知识": "",
        "信息": [
            "A股是中国大陆的股市",
            "阿里巴巴是一家世界级规模的公司"
        ],
        "输出": {
            "can_answer": "no",
            "analysis": "根据检索信息无法回答问题，检索的信息和问题均无关"
        }
    },
    "任务": {
        "问题": "$question",
        "领域知识": "$dk"
        "信息": $docs,
        "输出":
    }
}
"""
    template_en = template_zh

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["docs", "question", "dk"]

    def parse_response(self, response, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        return response
