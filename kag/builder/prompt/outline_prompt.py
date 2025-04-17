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

from typing import Optional, List

from kag.interface import PromptABC
import ast


@PromptABC.register("outline")
class OutlinePrompt(PromptABC):
    template_zh = """
{
    "instruction": "\n给定一段纯文本内容，请提取其中的标题，并返回一个列表。每个标题应包含以下信息：\n- 标题文本\n- 标题级别（例如 1 表示一级标题，2 表示二级标题等）\n\n假设标题遵循以下规则：\n1. 标题通常带有数字，我们的文本可能是从一些图片OCR生成的，所以标题可能隐藏在段落中，尽可能找出这些隐藏在段落中带有数字的标题\n2. 标题的级别可以通过以下方式推断：\n   - 一级标题：通常是篇章级别的内容。\n   - 二级标题：通常是章节级别的内容，具有简洁的文字描述，有时以 \"第X部分\"、\"第X章\"、\"Part X\" 等类似形式开头。\n   - 三级标题及以下：通常是段落或细节级别的标题，可能包含数字编号（如\"1.\"或\"1.1\"），或者较长且具体的描述（如\"1.1 子标题\"或\"第1节 概述\"）。\n3. 标题的级别也可以通过上下文判断：\n   - 如果两个标题之间的文本内容非常短（例如少于一定字数），后面的标题可能是更高或相同级别的标题。\n   - 连续编号的标题（如"第1条""第2条"）通常属于同一级别。\n   - 标题层级通常由其数字层次决定，例如"1""1.1""1.1.1"依次为 1 级、2 级、3 级。\n   - 如果一个标题包含关键词如"部分""章""节""条"，且其长度适中（例如 5 至 20 个字符），该标题的级别往往比更长或更短的标题要高。\n4. 以下标题可以直接忽略：\n   - 含有纯数字或仅由数字和标点组成的标题（例如"1."、"2.1"等）。\n   - 重复出现的标题（例如页眉或页脚被误识别为标题的情况）。\n5. 如果某些内容无法明确判断为标题，或者不符合上述规则，请忽略。\n\n请根据上述规则，返回一个包含标题和对应级别的列表，格式如下：\n[\n    (\"标题文本1\", 1),\n    (\"标题文本2\", 2),\n    (\"标题文本3\", 3),\n    ...\n]，我还会给你提供之前内容抽取出的目录current_outlines，你需要根据当前已经抽取的目录，自行判断抽取标题的粒度以及对应的等级",
    "input": "$input",
    "current_outline:": "$current_outline",
    "example": [
        {
            "input": "第8条 则\n\n1.各成员方在制订或修正其法律和规章时，可采取必要措施以保护公众健康和营养，并促进对其社会经济和技术发展至关重要部门的公众利益，只要该措施符合本协议规定。\n\n2.可能需要采取与本协议的规定相一致的适当的措施，以防止知识产权所有者滥用知识产权或藉以对贸易进行不合理限制或实行对国际间的技术转让产生不利影响的作法。\n\n第二部分 关于知识产权的效力、范围及使用的标准\n\n第1节 版权及相关权利\n\n第9条 与《伯尔尼公约》的关系",
            "output": [
                ("第8条 则",3),
                ("第二部分 关于知识产权的效力、范围及使用的标准",1),
                ("第1节 版权及相关权利",2),
                ("第9条 与《伯尔尼公约》的关系",3)
            ]
        },
        {
            "input": "第16条 授予权利\n\n1.已注册商标所有者应拥有阻止所有未经其同意的第三方在贸易中使用与已注册商标相同或相似的商品或服务的，其使用有可能招致混淆的相同或相似的标志。在对相同商品或服务使用相同标志的情况下，应推定存在混淆之可能。上述权利不应妨碍任何现行的优先权，也不应影响各成员方以使用为条件获得注册权的可能性。\n\n2.1967《巴黎公约》第6条副则经对细节作必要修改后应适用于服务。在确定一个商标是否为知名商标时，各成员方应考虑到有关部分的公众对该商标的了解，包括由于该商标的推行而在有关成员方得到的了解。\n\n3.1967《巴黎公约》第6条副则经对细节作必要修改后应适用于与已注册商标的商品和服务不相似的商品或服务，条件是该商标与该商品和服务有关的使用会表明该商品或服务与已注册商标所有者之间的联系，而且已注册商标所有者的利益有可能为此种使用所破坏。\n\n第17条 例外\n ",
            "output": [
                ("第16条 授予权利",3),
                ("第17条 例外",3)
            ]
        },
        {
            "input": "的做法。\n\n（4）此类使用应是非独占性的。\n\n（5）此类使用应是不可转让的，除非是同享有此类使用的那部分企业或信誉一道转让。\n\n（6）任何此类使用之授权，均应主要是为授权此类使用的成员方国内市场供应之目的。\n\n（7）在被授权人的合法利益受到充分保护的条件下，当导致此类使用授权的情况下不复存在和可能不再产生时，有义务将其终止；应有动机的请求，主管当局应有权对上述情况的继续存在进行检查。\n\n（8）考虑到授权的经济价值，应视具体情况向权利人支付充分的补偿金。\n\n（9）任何与此类使用之授权有关的决定，其法律效力应接受该成员方境内更高当局的司法审查或其他独立审查。\n\n（10）任何与为此类使用而提供的补偿金有关的决定，应接受成员方境内更高当局的司法审查或其他独立审查。\n",
            "output": []
        }
    ]
}
"""

    template_en = """
{
    "instruction": "\nGiven a text content, please extract the titles and return them as a list. Each title should include the following information:\n- Title text\n- Title level (e.g., 1 for first level, 2 for second level, etc.)\n\nAssume titles follow these rules:\n1. Titles usually contain numbers. Since our text might be OCR-generated from images, titles may be hidden within paragraphs. Try to identify these numbered titles hidden in paragraphs.\n2. Title levels can be inferred through:\n   - Level 1: Usually document-level content.\n   - Level 2: Usually chapter-level content, with concise descriptions, sometimes starting with \"Part X\", \"Chapter X\", etc.\n   - Level 3 and below: Usually paragraph or detail-level titles, may include numerical prefixes (like \"1.\" or \"1.1\") or longer specific descriptions.\n3. Title levels can also be determined by context:\n   - If the text between two titles is very short, the latter title might be of higher or same level.\n   - Consecutively numbered titles (like \"Article 1\", \"Article 2\") are usually of the same level.\n   - Title hierarchy is often determined by number levels, e.g., \"1\", \"1.1\", \"1.1.1\" are levels 1, 2, 3 respectively.\n   - Titles containing keywords like \"Part\", \"Chapter\", \"Section\" with moderate length (5-20 characters) often have higher levels than longer or shorter titles.\n4. Ignore the following titles:\n   - Pure numbers or titles consisting only of numbers and punctuation (e.g., \"1.\", \"2.1\").\n   - Repeated titles (e.g., headers/footers misidentified as titles).\n5. If content cannot be clearly identified as a title or doesn't match these rules, ignore it.\n\nPlease return a list of titles with their corresponding levels in the following format:\n[\n    (\"Title text 1\", 1),\n    (\"Title text 2\", 2),\n    (\"Title text 3\", 3),\n    ...\n]. I will also provide the previously extracted outline as current_outlines, and you need to judge the granularity and corresponding levels of title extraction based on the current outline.",
    "input": "$input",
    "current_outline": "$current_outline",
    "example": [
        {
            "input": "Article 8 Principles\n\n1. In formulating or amending their laws and regulations...\n\nPart Two: Standards Concerning the Availability, Scope and Use of Intellectual Property Rights\n\nSection 1 Copyright and Related Rights\n\nArticle 9 Relationship with the Berne Convention",
            "output": [
                ("Article 8 Principles", 3),
                ("Part Two: Standards Concerning the Availability, Scope and Use of Intellectual Property Rights", 1),
                ("Section 1 Copyright and Related Rights", 2),
                ("Article 9 Relationship with the Berne Convention", 3)
            ]
        },
        {
            "input": "Article 16 Grant of Rights\n\n1. Owners of registered trademarks...\n\nArticle 17 Exceptions",
            "output": [
                ("Article 16 Grant of Rights", 3),
                ("Article 17 Exceptions", 3)
            ]
        },
        {
            "input": "by doing so.\n\n(4) The use of this category should be non-exclusive...",
            "output": []
        }
    ]
}    
"""

    def __init__(self, language: Optional[str] = "zh"):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["input", "current_outline"]

    def parse_response(self, response: str, **kwargs):
        # 如果返回结果是字符串，先去除 Markdown 语法，再使用 ast.literal_eval 转换成列表
        if isinstance(response, str):
            cleaned_data = response.strip("`python\n[] \n")  # 去除 Markdown 语法和多余的空格
            cleaned_data = "[" + cleaned_data + "]"  # 恢复为列表格式
            try:
                parsed_data = ast.literal_eval(cleaned_data)
            except Exception as e:
                raise ValueError("无法解析返回的字符串为列表") from e
            response = parsed_data

        # 如果返回结果为字典且包含 "output" 键，则使用该键的值
        if isinstance(response, dict) and "output" in response:
            response = response["output"]

        # 如果 response 是以平铺方式呈现的列表（偶数索引位置均为字符串），则转换成标题与等级的元组列表
        if isinstance(response, list) and all(
            isinstance(response[i], str) for i in range(0, len(response), 2)
        ):
            paired_list = []
            i = 0
            while i < len(response):
                title = response[i]
                if i + 1 < len(response):
                    raw_level = response[i + 1]
                    # 如果 raw_level 不是整数，则尝试转换
                    if not isinstance(raw_level, int):
                        raw_level_str = str(raw_level).strip()
                        if raw_level_str.isdigit():
                            level = int(raw_level_str)
                        else:
                            level = paired_list[-1][1] if paired_list else 3
                    else:
                        level = raw_level
                    paired_list.append((title, level))
                    i += 2
                else:
                    level = paired_list[-1][1] if paired_list else 3
                    paired_list.append((title, level))
                    i += 1
            return paired_list

        # 如果返回结果不是平铺列表，而已经是类似元组列表，则需要智能处理潜在的拆包问题
        outline = kwargs.get("outline", [])
        for r in response:
            # 如果 r 是空列表或者空元组，则跳过该元素
            if isinstance(r, (list, tuple)):
                if not r:
                    continue  # 遇到空列表直接跳过
                # 如果元组中存在超过两个元素，则只取前两个（后面的元素忽略）
                if len(r) >= 2:
                    title, raw_level = r[0], r[1]
                else:
                    title = r[0]
                    raw_level = outline[-1][1] if outline else 3
                # 如果 raw_level 不是整数，则尝试转换
                if not isinstance(raw_level, int):
                    raw_level_str = str(raw_level).strip()
                    if raw_level_str.isdigit():
                        level = int(raw_level_str)
                    else:
                        level = outline[-1][1] if outline else 3
                else:
                    level = raw_level
                outline.append((title, level))
            else:
                # 非列表或元组的元素直接跳过
                continue

        return outline
