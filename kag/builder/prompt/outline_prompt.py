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
from typing import Optional, List

from kag.common.base.prompt_op import PromptOp


class OutlinePrompt(PromptOp):
    template_zh = """
{
    "instruction": "\n请理解input字段中的文本内容，识别文本的结构和组成部分，并帮我提取出以下内容的标题，可能有多个标题分散在文本的各个地方，仅返属于原文的回标题文本即可，不要返回其他任何内容，须按照python list的格式回答，具体形式请遵从example字段中给出的若干例子。",
    "input": "$input",
    "example": [
        {
            "input": "第8条 原 则

1.各成员方在制订或修正其法律和规章时，可采取必要措施以保护公众健康和营养，并促进对其社会经济和技术发展至关重要部门的公众利益，只要该措施符合本协议规定。

2.可能需要采取与本协议的规定相一致的适当的措施，以防止知识产权所有者滥用知识产权或藉以对贸易进行不合理限制或实行对国际间的技术转让产生不利影响的作法。

第二部分 关于知识产权的效力、范围及使用的标准

第1节 版权及相关权利

第9条 与《伯尔尼公约》的关系",
            "output": [
                "第8条 原 则",
                "第二部分 关于知识产权的效力、范围及使用的标准",
                "第1节 版权及相关权利",
                "第9条 与《伯尔尼公约》的关系"
            ],
        },
        {
            "input": "第16条 授予权利

1.已注册商标所有者应拥有阻止所有未经其同意的第三方在贸易中使用与已注册商标相同或相似的商品或服务的，其使用有可能招致混淆的相同或相似的标志。在对相同商品或服务使用相同标志的情况下，应推定存在混淆之可能。上述权利不应妨碍任何现行的优先权，也不应影响各成员方以使用为条件获得注册权的可能性。

2.1967《巴黎公约》第6条副则经对细节作必要修改后应适用于服务。在确定一个商标是否为知名商标时，各成员方应考虑到有关部分的公众对该商标的了解，包括由于该商标的推行而在有关成员方得到的了解。

3.1967《巴黎公约》第6条副则经对细节作必要修改后应适用于与已注册商标的商品和服务不相似的商品或服务，条件是该商标与该商品和服务有关的使用会表明该商品或服务与已注册商标所有者之间的联系，而且已注册商标所有者的利益有可能为此种使用所破坏。

第17条 例 外\n ",
            "output": [
                "第16条 授予权利",
                "第17条 例 外"
            ],
        },
        {
            "input":"的做法。

（4）此类使用应是非独占性的。

（5）此类使用应是不可转让的，除非是同享有此类使用的那部分企业或信誉一道转让。

（6）任何此类使用之授权，均应主要是为授权此类使用的成员方国内市场供应之目的。

（7）在被授权人的合法利益受到充分保护的条件下，当导致此类使用授权的情况下不复存在和可能不再产生时，有义务将其终止；应有动机的请求，主管当局应有权对上述情况的继续存在进行检查。

（8）考虑到授权的经济价值，应视具体情况向权利人支付充分的补偿金。

（9）任何与此类使用之授权有关的决定，其法律效力应接受该成员方境内更高当局的司法审查或其他独立审查。

（10）任何与为此类使用而提供的补偿金有关的决定，应接受成员方境内更高当局的司法审查或其他独立审查。
",
            "output": [],
        },
    ]
}    
    """

    template_en = """
{
    "instruction": "\nUnderstand the text content in the input field, identify the structure and components of the text, and help me extract the titles from the following content. There may be multiple titles scattered throughout the text. Only return the title texts that belong to the original text, and do not return any other content. The response must be in the format of a Python list, and the specific form should follow the examples given in the example field.",
    "input": "$input",
    "example": [
        {
            "input": "Article 8 Principles

1. In formulating or amending their laws and regulations, Members may take necessary measures to protect public health and nutrition, and to promote the public interest in sectors of vital importance to their socio-economic and technological development, provided that such measures are consistent with the provisions of this Agreement.

2. Appropriate measures may be needed to prevent the abuse of intellectual property rights by owners, or to prevent practices that restrict trade unjustifiably or adversely affect the international transfer of technology, in conformity with the provisions of this Agreement.

Part Two: Standards Concerning the Availability, Scope and Use of Intellectual Property Rights

Section 1 Copyright and Related Rights

Article 9 Relationship with the Berne Convention
",
            "output": [
                "Article 8 Principles",
                "Part Two: Standards Concerning the Availability, Scope and Use of Intellectual Property Rights",
                "Section 1 Copyright and Related Rights",
                "Article 9 Relationship with the Berne Convention"
            ],
        },
        {
            "input": "Article 16 Grant of Rights

1. Owners of registered trademarks shall have the right to prevent all third parties from using, without their consent, in the course of trade, any identical or similar signs for goods or services that are identical or similar to those for which the trademark is registered, where such use is likely to cause confusion. In the case of identical signs being used for identical goods or services, a likelihood of confusion shall be presumed. The above rights shall not prejudice any existing priority rights, nor shall they affect the possibility for Members to obtain registration rights conditional upon use.

2. The provisions of Article 6bis of the Paris Convention of 1967 shall apply to services with necessary modifications to the details. In determining whether a trademark is well-known, Members shall take into account the knowledge of the relevant public about that trademark, including the knowledge acquired in the relevant Member due to the promotion of that trademark.

3. The provisions of Article 6bis of the Paris Convention of 1967 shall apply to goods or services that are not similar to those for which the registered trademark is granted, provided that the use of the trademark in relation to those goods or services indicates a connection between the goods or services and the owner of the registered trademark, and that the interests of the owner of the registered trademark are likely to be harmed by such use.

Article 17 Exceptions
",
            "output": [
                "Article 16 Grant of Rights",
                "Article 17 Exceptions"
            ],
        },
        {
            "input": "by doing so.

(4) The use of this category should be non-exclusive.

(5) The use of this category should be non-transferable, unless it is transferred together with the part of the enterprise or reputation that enjoys the use of this category.

(6) Any authorization for such use should primarily be for the purpose of domestic market supply by the member party authorizing such use.

(7) There is an obligation to terminate it when the circumstances leading to the authorization for such use no longer exist and are unlikely to reoccur; upon motivated request, the competent authorities should have the right to examine the continued existence of the above circumstances.

(8) Adequate compensation should be paid to the right holder, taking into account the economic value of the authorization.

(9) Any decisions related to the authorization for such use should be subject to judicial review or other independent review by a higher authority within the territory of the member party.

(10) Any decisions related to the compensation provided for such use should be subject to judicial review or other independent review by a higher authority within the territory of the member party.",
            "output": [],    
        },
    ]
}    
    """

    def __init__(self, language: Optional[str] = "zh"):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        if isinstance(response, str):
            response = json.loads(response)
        if isinstance(response, dict) and "output" in response:
            response = response["output"]

        outline = kwargs.get("outline", [])
        for r in response:
            outline.append(r)

        return outline
