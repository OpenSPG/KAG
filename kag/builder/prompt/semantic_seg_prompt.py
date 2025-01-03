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
from typing import List

from kag.interface import PromptABC


@PromptABC.register("semantic_seg")
class SemanticSegPrompt(PromptABC):
    template_zh = """
{
    "instruction": "\n请理解input字段中的文本内容，识别文本的结构和组成部分，并按照语义主题确定分割点，将其切分成互不重叠的若干小节。如果文章有章节等可识别的结构信息，请直接按照顶层结构进行切分。\n请按照schema定义的字段返回，包含小节摘要和小节起始点。须按照JSON字符串的格式回答。具体形式请遵从example字段中给出的若干例子。",
    "schema": {
        "小节摘要": "该小节文本的简单概括",
        "小节起始点": "该小节包含的原文的起点，控制在20个字左右。该分割点将被用于分割原文，因此必须可以在原文中找到！"
    },
    "input": "$input",
    "example": [
        {
            "input": "周杰伦（Jay Chou），1979年1月18日出生于台湾省新北市，祖籍福建省永春县，华语流行乐男歌手、音乐人、演员、导演、编剧，毕业于淡江中学。\n2000年，在杨峻荣的推荐下，周杰伦开始演唱自己创作的歌曲。",
            "output": [
                {
                    "小节摘要": "个人简介",
                    "小节起始点": "周杰伦（Jay Chou），1979年1月18"
                },
                {
                    "小节摘要": "演艺经历",
                    "小节起始点": "\n2000年，在杨峻荣的推荐下"
                }
            ]
        },
        {
            "input": "杭州市灵活就业人员缴存使用住房公积金管理办法（试行）\n为扩大住房公积金制度受益面，支持灵活就业人员解决住房问题，根据国务院《住房公积金管理条例》、《浙江省住房公积金条例》以及住房和城乡建设部、浙江省住房和城乡建设厅关于灵活就业人员参加住房公积金制度的有关规定和要求，结合杭州市实际，制订本办法。\n一、本办法适用于本市行政区域内灵活就业人员住房公积金的自愿缴存、使用和管理。\n二、本办法所称灵活就业人员是指在本市行政区域内，年满16周岁且男性未满60周岁、女性未满55周岁，具有完全民事行为能力，以非全日制、个体经营、新就业形态等灵活方式就业的人员。\n三、灵活就业人员申请缴存住房公积金，应向杭州住房公积金管理中心（以下称公积金中心）申请办理缴存登记手续，设立个人账户。\n ",
            "output": [
                {
                    "小节摘要": "管理办法的制定背景和依据",
                    "小节起始点": "为扩大住房公积金制度受益面"
                },
                {
                    "小节摘要": "管理办法的适用范围",
                    "小节起始点": "一、本办法适用于本市行政区域内"
                },
                {
                    "小节摘要": "灵活就业人员的定义",
                    "小节起始点": "二、本办法所称灵活就业人员是指"
                },
                {
                    "小节摘要": "灵活就业人员缴存登记手续",
                    "小节起始点": "三、灵活就业人员申请缴存住房公积金",
                }
            ]
        }
    ]
}    
    """

    template_en = """
{
    "instruction": "\nPlease understand the content of the text in the input field, recognize the structure and components of the text, and determine the segmentation points according to the semantic theme, dividing it into several non-overlapping sections. If the article has recognizable structural information such as chapters, please divide it according to the top-level structure.\nPlease return the results according to the schema definition, including summaries and starting points of the sections. The format must be a JSON string. Please follow the examples given in the example field.",
    "schema": {
        "Section Summary": "A brief summary of the section text",
        "Section Starting Point": "The starting point of the section in the original text, limited to about 20 characters. This segmentation point will be used to split the original text, so it must be found in the original text!"
    },
    "input": "$input",
    "example": [
        {
            "input": "Jay Chou (Jay Chou), born on January 18, 1979, in Xinbei City, Taiwan Province, originally from Yongchun County, Fujian Province, is a Mandopop male singer, musician, actor, director, screenwriter, and a graduate of Tamkang Senior High School.\nIn 2000, recommended by Yang Junrong, Jay Chou started singing his own compositions.",
            "output": [
                {
                    "Section Summary": "Personal Introduction",
                    "Section Starting Point": "Jay Chou (Jay Chou), born on January 18"
                },
                {
                    "Section Summary": "Career Start",
                    "Section Starting Point": "\nIn 2000, recommended by Yang Junrong"
                }
            ]
        },
        {
            "input": "Hangzhou Flexible Employment Personnel Housing Provident Fund Management Measures (Trial)\nTo expand the benefits of the housing provident fund system and support flexible employment personnel to solve housing problems, according to the State Council's 'Housing Provident Fund Management Regulations', 'Zhejiang Province Housing Provident Fund Regulations' and the relevant provisions and requirements of the Ministry of Housing and Urban-Rural Development and the Zhejiang Provincial Department of Housing and Urban-Rural Development on flexible employment personnel participating in the housing provident fund system, combined with the actual situation in Hangzhou, this method is formulated.\n1. This method applies to the voluntary deposit, use, and management of the housing provident fund for flexible employment personnel within the administrative region of this city.\n2. The flexible employment personnel referred to in this method are those who are within the administrative region of this city, aged 16 and above, and males under 60 and females under 55, with full civil capacity, and employed in a flexible manner such as part-time, self-employed, or in new forms of employment.\n3. Flexible employment personnel applying to deposit the housing provident fund should apply to the Hangzhou Housing Provident Fund Management Center (hereinafter referred to as the Provident Fund Center) for deposit registration procedures and set up personal accounts.",
            "output": [
                {
                    "Section Summary": "Background and Basis for Formulating the Management Measures",
                    "Section Starting Point": "To expand the benefits of the housing provident fund system"
                },
                {
                    "Section Summary": "Scope of Application of the Management Measures",
                    "Section Starting Point": "1. This method applies to the voluntary deposit"
                },
                {
                    "Section Summary": "Definition of Flexible Employment Personnel",
                    "Section Starting Point": "2. The flexible employment personnel referred to in this method"
                },
                {
                    "Section Summary": "Procedures for Flexible Employment Personnel to Register for Deposit",
                    "Section Starting Point": "3. Flexible employment personnel applying to deposit the housing provident fund"
                }
            ]
        }
    ]
}    
    """

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        if isinstance(response, str):
            response = json.loads(response)
        if isinstance(response, dict) and "output" in response:
            response = response["output"]

        content = kwargs.get("input", "")

        seg_info = []
        for seg_point in response:
            if not isinstance(seg_point, dict):
                continue
            start = seg_point.get(
                "小节起始点" if self.language == "zh" else "Section Starting Point",
            )
            if not isinstance(start, str):
                continue
            start = start.strip()
            # use first 10 charathers for split
            loc = content.find(start)
            if loc == -1:
                print(f"incorrect seg: {seg_point}")
                continue

            abstract = seg_point.get(
                "小节摘要" if self.language == "zh" else "Section Summary", None
            )
            seg_info.append((loc, abstract))
        return seg_info
