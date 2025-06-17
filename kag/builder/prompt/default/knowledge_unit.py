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

import json
import re
from typing import List

from kag.builder.prompt.default.util import load_knowIE_data
from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import PromptABC


@PromptABC.register("knowledge_unit")
class KnowledgeUnitPrompt(PromptABC):
    template_en = """You are an assistant for document analysis and knowledge unit extraction. Please extract substantial discussions, arguments, or analyses from the input document chunks. Ensure that the extracted knowledge units are strictly related to the document's theme and are the core content that the author directly introduces, analyzes, or argues within the chunk.

### Extraction Requirements:
- Identify the core argument in the chunk and extract content that makes a creative contribution to the document's theme.
- If the chunk contains numerous citations or mentions, only extract significant knowledge units involved when further analyzing, expanding, arguing, or applying these contents. Exclude auxiliary knowledge units or background information that are merely cited or mentioned.
- The names of knowledge units should be described using concise and clear language, fully reflecting the core theme of the knowledge unit.
- A knowledge unit is a complete and coherent whole, with clear arguments. Multiple knowledge units may be extracted from a chunk, but if further division would fail to preserve the context, argumentation process, etc., of the knowledge unit, the entire chunk should not be subdivided further. The content description of knowledge units should be clear and organized, avoiding superfluous or repetitive explanations.

### Knowledge Types
- Declarative Knowledge: Narratives explaining concepts, terms, theorems, clauses, etc., answering 'what' questions, including concept definitions, term explanations, arguments, formulas, legal provisions, etc.
- Case Knowledge: Demonstrating and explaining abstract concepts and theories through specific situations or examples, including judicial precedents, math problems, medical cases, etc., usually treated as a single complete knowledge unit.
- Factual Knowledge: Describing the state, attributes, characteristics, or background information of things, including historical events, news information, entity introductions, etc.
- Procedural Knowledge: Knowledge about how to perform tasks or operations, including program code, algorithms, operational steps, experimental processes, equation sets for problem-solving, etc.
- Analytical Knowledge: Knowledge derived through logical analysis, calculations, induction, deduction, etc., to support views or conclusions, answering 'why' and 'how to derive conclusions' questions.


### Output Format:
{
  "knowledge unit 1 Name":
  { 
    "Content": "A text excerpt extracted or summarized from the chunk, must include critical information that unambiguously explains the knowledge unit's content and subject.",
    "Knowledge Type": "Declarative Knowledge / Case Knowledge / Factual Knowledge / Procedural Knowledge / Analytical Knowledge",
    "Structural Content": "Structured content associated with the knowledge unit, such as charts, formulas, code, rules, first-order logic representation, equation sets, data structure definitions, etc.",
    "Domain Ontology": "The hierarchical classification system of disciplines or professional fields to which knowledge units belong. It is important to note that the terms at each level are general concepts rather than specific instances (remove individual person, organizations, etc. for the ontology).",
    "Core Entities": "Keywords that represent the subject or characteristics of the knowledge unit, ensuring that each term is semantically complete and reflects the knowledge unit's distinctiveness in searches relative to other content, and the valid type of each core entity is listed in the `Entity Types`",
    "Related Query": "The three most relevant query questions based on the knowledge unit's subject and content",
    "Extended Knowledge Points": "Other highly related but divergent knowledge points not included in the current knowledge point"
 },
  "knowledge unit 2 Name": {},
  ……
}

### Example:
input:"No Mediocre" is a song by American rapper T.I., released on June 17, 2014, through Grand Hustle and Columbia Records, as the lead single from his ninth studio album "Paperwork" (2014). The song, produced by DJ Mustard, features a guest appearance from Grand Hustle protégé, Australian rapper Iggy Azalea.
output:
{
  "No Mediocre Song Details":{
    "Content": "\"No Mediocre\" is a song by American rapper T.I., released as the lead single from his ninth studio album \"Paperwork\" (2014). The track, produced by DJ Mustard, includes a guest appearance by Australian rapper Iggy Azalea. It peaked at number 69 on the US Billboard Hot 100 and was met with positive reviews for its production and Azalea's contribution.",
    "Knowledge Type": "Factual Knowledge",
    "Structural Content": "",
    "Domain Ontology": "Music -> Hip Hop -> T.I. Discography -> No Mediocre",
    "Core Entities": {"T.I.": "Person", "No Mediocre" : "Culture and Entertainment", "Paperwork" : "Culture and Entertainment", "DJ Mustard" : "Person", "Iggy Azalea": "Person", "US Billboard Hot 100": "Culture and Entertainment" },
    "Related Query": ["What is the lead single from T.I.'s ninth studio album?", "Who produced the song 'No Mediocre'?", "What was the peak position of 'No Mediocre' on the US Billboard Hot 100?"],
    "Extended Knowledge Points": ["T.I.'s discography", "DJ Mustard's production work", "Iggy Azalea's collaborations", "US Billboard Hot 100 chart", "Critical reception of 'No Mediocre'", "Soundtrack for 'Think Like a Man Too'"]
  }
}
### Input:
input: $input
"""

    template_zh = """你是一个文档分析及知识点提取助理，请从输入的文档片段（chunk）中提取出对文档主题的背景知识、涉事人物、时间、地点进行实施性描述和介绍，或实质性对内容中相关信息进行讨论、论述或分析的知识点。
请确保提取的知识点严格与文档的主题相关，且是文档作者在片段中直接介绍、分析或论证的核心内容。
如果无法确认知识点所描述的主体，而文档核心实体信息在input中有提供时，请参考。

### 提取要求：
1.确定片段中的核心论述对象，提取那些对文档主题有创造性贡献的内容。
2.如果片段中出现较多引用或提及的内容，仅提取针对这些内容进一步分析、拓展、论证或应用时所涉及的重要知识点。不要包括引用、提到的辅助知识点或背景内容。
3.知识点的名称，应使用简洁、明确的语言描述，并完整体现知识点的核心主题；
4.一个知识点，是一个叙述完整、论述清晰的整体。chunk中提取到的知识点可能有多个：当围绕同一主题或主体从多个方面并行讨论时，请拆成多个知识点；当进一步拆分无法完整保留知识点的前因后果、论述过程等信息，则整个片段作为1个知识点不要再细分。
5.知识点的内容描述条理清晰，避免多余或重复的解释。

### 知识类型
陈述性知识：对领域的概念、术语、定理、条款等的叙述说明，回答“是什么”的问题，包括概念定义、术语解释、论述、公式、法律法条等。
案例类知识：通过具体情境、实例，体现和解释说明抽象的概念和理论，包括司法判例、数学例题、医疗病例等，一般一个案例被作为1个完整的知识点。
事实性知识：描述事物的状态、属性、特征或背景信息，包括历史事件、新闻资讯、实体介绍等。
过程类知识：关于如何执行任务或操作的知识，包括程序代码、算法、操作步骤、实验过程、解题过程的方程组等。
推理类知识：通过通过逻辑分析、计算、归纳、演绎等方式得出的知识来支持观点或结论，它回答“为什么”和“如何得出结论”的问题。

### 输出格式:
{
  "知识点1名称": 
  {
    "内容": "从chunck中提取或总结的描述知识的文本片段，必须包括能够无歧义的说明知识点内容和主体的关键信息。", 
    "知识类型": "陈述性知识/案例类知识/事实性知识/操作类知识/分析类知识”,
    "结构化内容": "知识点关联的图表、公式、代码、规则、一阶逻辑表示、方程组、数据结构定义等结构化内容"
    "领域本体": "知识点所属学科或专业领域的上下位分类体系"
    "核心实体": "体现知识点主体或知识点特征的keyword关键词，注意每个实体词需要语义完整性并能体现知识点在检索时相对于其他内容的区分度"
    "关联问": "根据知识点主体和内容所能回答的query问题",
    "扩展知识点": "当前知识点不包含但高度相关的、发散性的其他知识"
  },
  "知识点2名称": {},
  ……
}

### Example:
input: 
2019 年 1-12 月,全国发电量 71422 亿千瓦时,同比增长 3.5%,增速比上年同期回落 3.3pct。从各种发电方式发电量来看：\n* 火电发电量 51654 亿千瓦时,同比增长 1.9%,增速同比回落 4.1 pct。\n◆ 水电发电量 11534 亿千瓦时,同比增长 4.8%,增速同比提高 0.7pct。\n◆ 核电发电量 3484 亿千瓦时,同比增长 18.3%,增速同比回落 0.4pct。\n◆ 风电发电量 3577 亿千瓦时,同比增长 7.0%,增速同比回落 9.6 pct。\n◆ 太阳能发电量 1172 亿千瓦时,同比增长 13.3%,增速同比回落 6.3pct。\n图44：各发电方式累计发电量同比增速 (%)\n资料来源：国家统计局,申港证券研究所\n图45：各发电方式当月发电量比例 (%)\n资料来源：国家统计局,申港证券研究所
output: {
  "2019年全国火电发电量": {
    "内容": "2019年全国火电发电量51654亿千瓦时，同比增长1.9%，增速同比回落4.1个百分点",
    "知识类型": "事实性知识",
    "结构化内容": "",
    "领域本体": "能源统计 -> 电力生产 -> 发电方式分类 -> 火力发电",
    "核心实体": "火电发电量,同比增长率,2019年",
    "关联问": ["2019年全国火电发电量是多少？", "火电发电量增速变化趋势"],
    "扩展知识点": ["2018年全国火电发电量","火力发电方法"]
  },
  "2019年全国水电发电量": {
    "内容": "2019年全国水电发电量11534亿千瓦时，同比增长4.8%，增速同比提高0.7个百分点",
    "知识类型": "事实性知识",
    "结构化内容": "",
    "领域本体": "能源统计 -> 电力生产 -> 发电方式分类 -> 水力发电",
    "核心实体": "水电发电量,增速提升,2019年",
    "关联问": ["水电发电量在2019年增长情况", ],
    "扩展知识点": ["2018年全国水电发电量","水电与火电增速对比", "清洁能源发展数据"]   
  },
  "2019年全国核电发电量": {
    "内容": "2019年全国核电发电量3484亿千瓦时，同比增长18.3%，增速同比回落0.4个百分点",
    "知识类型": "事实性知识",
    "结构化内容": "",
    "领域本体": "能源统计 -> 电力生产 -> 发电方式分类 -> 核能发电",
    "核心实体": "核电发电量,高增速,2019年",
    "关联问": ["2019核电的发电增速数据"],
    "扩展知识点": ["2018年全国核电发电量","清洁能源发展现状分析", "核能发电增长原因"]   
  },
  "2019年全国风电发电量": {
    "内容": "2019年全国风电发电量3577亿千瓦时，同比增长7.0%，增速同比回落9.6个百分点",
    "知识类型": "事实性知识",
    "结构化内容": "",
    "领域本体": "能源统计 -> 电力生产 -> 发电方式分类 -> 风力发电",
    "核心实体": "风电发电量,增速下降,2019年",
    "关联问": ["风力发电量变化趋势"],
    "扩展知识点": ["2018年全国风电发电量", "风电与光伏增速对比", "可再生能源发展评估"]   
  },
  "2019年全国太阳能发电量": {
    "内容": "2019年全国太阳能发电量1172亿千瓦时，同比增长13.3%，增速同比回落6.3个百分点",
    "知识类型": "事实性知识",
    "结构化内容": "",
    "领域本体": "能源统计 -> 电力生产 -> 发电方式分类 -> 太阳能发电",
    "核心实体": "太阳能发电量,增速变化,2019年",
    "关联问": ["2019年全国太阳能发电增长数据"],
    "扩展知识点": ["2018年全国火电发电量","太阳能的定义","太阳能与风能发展对比", "2019年可再生能源总发电量"]   
  },
  "2019年全国全国发电总量与结构": {
    "内容": "2019年全国发电总量71422亿千瓦时，同比增长3.5%。其中火电占比72.3%，水电占比16.15%，核电占比4.88%，风电占比5.01%，太阳能占比1.64%",
    "知识类型": "事实性知识",
    "结构化内容": "",
    "领域本体": "能源统计 -> 电力生产 -> 总体发电数据分析",
    "核心实体": "发电总量结构,同比增长,2019年",
    "关联问": ["2019年发电量结构分布", "2019年全国发电总量中不同类型发电量的占比"],
    "扩展知识点": ["2018年全国发电总量与结构","发电方法"]   
  }
}
### Input:
input: $input
"""

    @property
    def template_variables(self) -> List[str]:
        return ["input", "named_entities"]

    def modify_knowledge_unit(self, text, lang="zh"):
        # 定义正则表达式模式
        if lang == "zh":

            pattern = r'"知识点\d+名称"\s*:\s*"([^"]+)"\s*,'
        else:
            pattern = r'"knowledge unit \d+ Name"\s*:\s*"([^"]+)",'
        # 使用re.sub函数进行替换
        # print(pattern)
        modified_text = re.sub(pattern, r'"\1":', text)

        # print("modified_text:",modified_text)
        return modified_text

    def process_data(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        return rsp

    def process_en(self, response: dict, **kwargs):
        """ "No Mediocre Song Details":{
          "Content": "\"No Mediocre\" is a song by American rapper T.I., released as the lead single from his ninth studio album \"Paperwork\" (2014). The track, produced by DJ Mustard, includes a guest appearance by Australian rapper Iggy Azalea. It peaked at number 69 on the US Billboard Hot 100 and was met with positive reviews for its production and Azalea's contribution.",
          "Knowledge Type": "Factual Knowledge",
          "Structural Content": "",
          "Domain Ontology": "Music -> Hip Hop -> T.I. Discography -> No Mediocre",
          "Core Entities": "T.I., No Mediocre, Paperwork, DJ Mustard, Iggy Azalea, US Billboard Hot 100",
          "Related Query": ["What is the lead single from T.I.'s ninth studio album?", "Who produced the song 'No Mediocre'?", "What was the peak position of 'No Mediocre' on the US Billboard Hot 100?"],
          "Extended Knowledge Points": ["T.I.'s discography", "DJ Mustard's production work", "Iggy Azalea's collaborations", "US Billboard Hot 100 chart", "Critical reception of 'No Mediocre'", "Soundtrack for 'Think Like a Man Too'"]
        }"""
        ret = {}
        if "Content" in response.keys():
            ret["content"] = response["Content"]
        if "Knowledge Type" in response.keys():
            ret["knowledgetype"] = response["Knowledge Type"]
        if "Domain Ontology" in response.keys():
            ret["ontology"] = response["Domain Ontology"]
        if "Core Entities" in response.keys():
            ret["core_entities"] = response["Core Entities"]
        if "Related Query" in response.keys():
            ret["relatedQuery"] = response["Related Query"]
        if "Extended Knowledge Points" in response.keys():
            ret["extendedKnowledge"] = response["Extended Knowledge Points"]
        return ret

    def process_zh(self, response: dict, **kwargs):
        """ "2019年全国全国发电总量与结构": {
          "内容": "2019年全国发电总量71422亿千瓦时，同比增长3.5%。其中火电占比72.3%，水电占比16.15%，核电占比4.88%，风电占比5.01%，太阳能占比1.64%",
          "知识类型": "事实性知识",
          "结构化内容": "",
          "领域本体": "能源统计 -> 电力生产 -> 总体发电数据分析",
          "核心实体": "发电总量结构,同比增长,2019年",
          "关联问": ["2019年发电量结构分布", "2019年全国发电总量中不同类型发电量的占比"],
          "扩展知识点": ["2018年全国发电总量与结构","发电方法"]
        }"""
        ret = {}
        if "内容" in response.keys():
            ret["content"] = response["内容"]
        if "知识类型" in response.keys():
            ret["knowledgetype"] = response["知识类型"]
        if "领域本体" in response.keys():
            ret["ontology"] = response["领域本体"]
        if "核心实体" in response.keys():
            ret["core_entities"] = response["核心实体"]
        if "关联问" in response.keys():
            ret["relatedQuery"] = response["关联问"]
        if "扩展知识点" in response.keys():
            ret["extendedKnowledge"] = response["扩展知识点"]
        return ret

    def parse_response(self, response: str, **kwargs):
        # response = self.modify_knowledge_unit(response,lang = KAG_PROJECT_CONF.language)
        # rsp = self.process_data(response)
        rsp = load_knowIE_data(response)
        ret = {}
        for k, v in rsp.items():
            ret[k] = (
                self.process_en(v, **kwargs)
                if KAG_PROJECT_CONF.language == "en"
                else self.process_zh(v, **kwargs)
            )
        return ret
