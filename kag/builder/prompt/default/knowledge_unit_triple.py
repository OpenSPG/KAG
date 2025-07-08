# -*- coding: utf-8 -*-
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

from typing import List

from kag.builder.prompt.default.util import load_SPO_data
from kag.interface import PromptABC


@PromptABC.register("knowledge_unit_triple")
class OpenIEKnowledgeUnitTriplePrompt(PromptABC):
    template_en = """You are an expert specializing in knowledge graph relation extraction. Please refer to the given entity list to extract potential relations between any entities from the provided text, and list them in quadruple format. 
If no relations are found, there is no need to list anything.
Please respond in JSON list format, where:

The overall structure is a list of quadruples and each quadruple is also a list. The output format is as follows:
[
    [subject entity, predicate, object entity, specific condiction],
    []
]

Please note the following requirements:
- The subject entity and object entity must either come from the provided entity_list or be meaningful noun phrases or proper nouns.
- Strictly prohibit object entities from containing meaningless terms: numeric values ("18 people"), dates ("December 1959"), pronouns ("there"), or ambiguous nouns ("current site").
- Predicates are typically semantic gerunds, verbs, or phrases that indicate actions, behaviors, or the connections between entities. The representation of predicates is directional, so it's advisable to avoid using prepositions such as "is" or "by." For instance, ["Zhi Xin Fund", "partner", "Liang Xiaodong"] is better than ["Liang Xiaodong", "acts as partner", "Zhi Xin Fund"].
- Specific constraints denote validity conditions (e.g., time, location). Use commas for multiple constraints. Leave empty if none exist.
- Each quadruplet must contain exactly four elements, separated by commas.

### Example:
input:SolarTech Innovations, a renewable energy startup headquartered in Berlin, unveiled its latest product 'EcoGrid Battery' during the annual Clean Energy Summit in June 2023. The advanced energy storage system was co-developed with OceanWave Labs, utilizing their marine-based cooling technology. CEO Dr. Helena Weiss confirmed the product will be distributed through GreenHub Stores across Europe starting Q1 2024. Technical specifications reveal the battery integrates patented 'NanoCool' modules, a breakthrough first presented at last year's Berlin Tech Expo. Environmental analysts predict this collaboration could reduce urban carbon emissions by 40% within five years. 
entity_list: [
  ("SolarTech Innovations", "Organization"),
  ("EcoGrid Battery", "Technology"),
  ("OceanWave Labs", "Organization"),
  ("Dr. Helena Weiss", "Person"),
  ("NanoCool modules", "Technology"),
  ("Clean Energy Summit", "Event"),
  ("GreenHub Stores", "Organization")
]
output: [
  ["SolarTech Innovations", "unveiling", "EcoGrid Battery", "June 2023, Clean Energy Summit"],
  ["SolarTech Innovations", "co-developing", "OceanWave Labs", ""],
  ["EcoGrid Battery", "integrating", "NanoCool modules", ""],
  ["Dr. Helena Weiss", "announcing distribution", "GreenHub Stores", "Q1 2024"],
  ["OceanWave Labs", "providing", "marine-based cooling technology", ""]
]
### Input:
input: $input
entity_list: $entity_list
"""

    template_zh = """你是一位专注于知识图谱关系抽取的专家。请参考给定实体列表，从给定的文本中提取任何实体之间可能的关系，并按照四元组列表的格式列出它们。如果没有找到任何关系，则无需列出。
请以JSON列表的格式响应，整体为一个list，其中每一个四元组也为list，格式为：
[
  [主语实体, 谓词, 宾语实体, 特定约束],
  []
]

请注意以下要求：
1、主语实体和宾语实体要么是下面给出的实体列表中涉及的实体，要么是有意义的实体名词或专有名词，可以适当添加修饰语使实体的描述更加准确，例如“免费停车服务”
2、严格禁止宾语实体使用无意义词语如具体数值("18人")，日期("1959年12月")，代词("那里")，不明确的名词("现址")。
3、谓词多为语义明确的动名词，动词等关系型词语，或者短语。表示动作、行为或者实体之间的联系和关系。谓词的表述具有方向性的，请采取最佳的方向且避免使用"是""由"等介词，例如["挚信资本", "合伙人", "梁晓东]优于["梁晓东", "担任合伙人", "挚信资本"]
4、特定约束是决定“主谓宾”构成的句子成立时的有效性条件或约束，例如特定的发生时间、具体地点等，多个约束条件使用逗号并列。如果不存在特定条件，请将其留为空字符串。
5、严格确保四元组刚好包含四个元素，用逗号分隔。

### Example
输入:标题: 中共当阳市委党校:当阳市境内学校 (社会/学校)
内容: #中共当阳市委党校:当阳市境内学校\n中共当阳市委党校、当阳市行政学校位于当阳市环城西路129号，是市委、市政府直属的正科级事业单位。\n中文名：中共当阳市委党校。创办时间：1959年12月。现任校长：沈建华。所属地区：当阳市。\n##发展历程\n中共当阳市委党校创办于1959年12月，1960年停办。1972年复校，校址设在原玉阳镇雄风大队娘娘庙。1974年2月，迁至官当（原海军五七干校）。1975年2月，根据县委的指示，增设当阳县五七干校。1978年8月，奉命撤消五七干校。1984年，为落实《中共中央关于实现党校教育正规化的决定》，从官当迁至现址。1985年4月，经省有关部门批准为中专体制县级党校。1994年5月，经市委、市政府批准兼办行政学校，主要负责国家公务员的培训。1998年10月，经省委党校、宜昌市委党校批准，成立学历教育函授站，主要负责在职干部的学历培训。\n##师资力量\n中共当阳市委党校、当阳市行政学校现有教职工(在编在职) 18人，其中，国家公务员12人，专业技术人员5人，工勤人员1人。\n##内设机构\n中共当阳市委党校、当阳市行政学校内设办公室、组教科、社会教育科、总务科等4个科室；校委下设机关党支部和离退休党支部2个党支部。\n##教学设施\n学校现有标准化教室4间（每间50座）、阶梯教室1间（430座）、大教室1间（100座），多媒体教室1间（50座），学员宿舍1栋，有床位150张。常年培训干部500人左右。\n中共当阳市委党校、当阳市行政学校占地54亩，建筑面积9800平方米。校园绿化率、道路硬化率均达到100%，多次被评为当阳市“文明单位”、“花园式学校”，宜昌市党校系统“先进单位”，全省党校系统“九五”评估达标“合格学校”。\n##领导班子\n当阳市委常委、组织部长、市委党校校长：孟 丽\n党委书记、常务副校长：沈建华\n党委委员、副 校 长：万 喆\n党委委员、副 校 长：卢建枝\n党委委员、工会主席：徐海峰。
实体列表: [
    ("中共当阳市委党校", "组织机构"),
    ("当阳市行政学校", "组织机构"),
    ("沈建华", "人物"),
    ("孟丽", "人物"),
    ("万喆", "人物"),
    ("卢建枝", "人物"),
    ("徐海峰", "人物"),
    ("当阳市", "地理位置"),
    ("玉阳镇雄风大队娘娘庙", "地理位置"),
    ("官当", "地理位置"),
    ("当阳县五七干校", "组织机构")
]
output: [
    ["中共当阳市委党校", "位于", "当阳市环城西路129号", ""],
    ["中共当阳市委党校", "现任校长", "沈建华", ""],
    ["中共当阳市委党校", "所属地区", "当阳市", ""],
    ["中共当阳市委党校", "创办时间", "1959年12月", ""],
    ["中共当阳市委党校", "停办时间", "1960年", ""],
    ["中共当阳市委党校", "复校时间", "1972年", ""], 
    ["中共当阳市委党校", "校址设在", "玉阳镇雄风大队娘娘庙", "1972年复校时"],
    ["中共当阳市委党校", "迁至", "官当", "1974年2月"],
    ["中共当阳市委党校", "增设", "当阳县五七干校", "1975年2月"],
    ["中共当阳市委党校", "兼办", "当阳市行政学校", "1994年5月"],
    ["中共当阳市委党校", "成立", "学历教育函授站", "1998年10月"],
    ["中共当阳市委党校", "内设", "办公室", ""],
    ["中共当阳市委党校", "内设", "组教科", ""],
    ["中共当阳市委党校", "内设", "社会教育科", ""],
    ["中共当阳市委党校", "内设", "总务科", ""],
    ["中共当阳市委党校", "下设", "机关党支部", ""],
    ["中共当阳市委党校", "下设", "离退休党支部", ""],
    ["中共当阳市委党校", "被评为", "当阳市文明单位", ""],
    ["中共当阳市委党校", "被评为", "花园式学校", ""],
    ["中共当阳市委党校", "被评为", "宜昌市党校系统先进单位", ""],
    ["中共当阳市委党校", "被评为", "全省党校系统九五评估达标合格学校", ""],
    ["当阳市行政学校", "位于", "当阳市环城西路129号", ""],
    ["当阳市行政学校", "主要负责", "国家公务员的培训", ""],
    ["孟丽", "担任", "当阳市委常委", ""],
    ["孟丽", "担任", "组织部长", ""],
    ["孟丽", "担任", "中共当阳市委党校校长", ""],
    ["沈建华", "担任", "中共当阳市委党校党委书记", ""],
    ["沈建华", "担任", "中共当阳市委党校常务副校长", ""],
    ["万喆", "担任", "中共当阳市委党校党委委员", ""],
    ["万喆", "担任", "中共当阳市委党校副校长", ""],
    ["卢建枝", "担任", "中共当阳市委党校党委委员", ""],
    ["徐海峰", "担任", "中共当阳市委党校党委委员", ""],
    ["徐海峰", "担任", "中共当阳市委党校工会主席", ""],
    ["当阳县五七干校", "撤销于", "中共当阳市委党校", "1978年8月"]
]
### Input:
输入:$input
实体列表:$entity_list
"""

    @property
    def template_variables(self) -> List[str]:
        return ["entity_list", "input"]

    def parse_response(self, response: str, **kwargs):
        standardized_triples = load_SPO_data(response)
        return standardized_triples
