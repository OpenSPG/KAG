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
# flake8: noqa
import json
import re
from typing import List, Dict
from kag.interface import PromptABC, Task


@PromptABC.register("context_select_prompt")
class ContextSelectPrompt(PromptABC):
    template_en = """
The Question field is the user's question, and Context is a batch of articles retrieved from the knowledge base that may contain the answer to the question. Please carefully analyze the question and each context, and return up to 5 contexts that may contain the answer to the question, and answer the question. If you think all the retrieved contexts are irrelevant to the question, return an empty list and set the answer to UNKNOWN. 
Note: 
1. response must be json format, only json format, without explanation
2. The return format refers to the example：

Question:
who is the performer of Hello Love?

Context:
{'idx': 0,
 'content': '"Hello Love" is a 1974 single by Hank Snow. "Hello Love" was Snow\'s seventh and final number one on the U.S. country singles chart, and his first number one in twelve years. The single stayed at number one for a single week and spent a total of ten weeks on the chart.',
}
    
{'idx': 1,
   'content': '"Your Love Is a Song" was written and recorded by the alternative rock band Switchfoot. It was first released as a single to the iTunes Store in Australia, and became the third radio single from the band\'s seventh studio album, "Hello Hurricane".'
}
    
{'idx': 2,
   'content': '"Will to Love" is a song written by Neil Young that was first released on his 1977 album "American Stars \'N Bars". A promotional single of "Will to Love" was released, backed with a live performance of "Cortez the Killer."'
}
    
Answer:
{
  "context": [0],
  "answer": "Hank Snow"
}

    
Question:
Which state borders Tennessee to the east?
    
Context:
{'idx': 0,
   'content': 'In 2013, Ulta opened 125 stores in the United States, bringing their total number of locations to 675 stores. They also announced plans to open 100 more locations by the end of 2014. As of August 4, 2018, Ulta operates 1,124 stores in 49 states and the District of Columbia. A majority of Ulta Beauty stores are located in the East Coast region, although California also has a large presence of company - owned stores.',    
}
    
{'idx': 1,
   'content': 'She was born and raised in Sollentuna, Stockholm, Sweden but has lived for many years in Gothenburg. Maia became known through Annika Norlin\'s band Hello Saferide, where she is a back-up singer. Her solo career began in early 2007 when the song "And I Found This Boy" started being played heavily on Swedish radio. The single was followed up by the album "Though, I\'m Just Me" and the single "Gothenburg". During the summer of 2007 she toured around Sweden, playing at such shows as Allsång på Skansen, Hultsfredsfestivalen, Peace & Love and Arvika Festival. In 2010 she for the first time released material in Swedish with the EP "Dröm bort mig igen".',    
}
    
{'idx': 2,
   'content': 'Publix Super Markets, Inc., commonly known as Publix, is an employee - owned, American supermarket chain headquartered in Lakeland, Florida. Founded in 1930 by George W. Jenkins, Publix is a private corporation that is wholly owned by present and past employees. It is considered the largest employee - owned company in the world. Publix operates throughout the Southeastern United States, with locations in Florida (785), Georgia (186), Alabama (68), South Carolina (58), Tennessee (42), North Carolina (35), and Virginia (8).',    
}
    
Answer:
{
  "context": [],
  "answer": "UNKNOWN"
}
"""

    template_zh = """
问题字段是用户的问题，Context是从知识库中检索到的可能包含问题答案的一批文章。请仔细分析问题和每个上下文，返回最多5个可能包含问题答案的上下文，并回答问题。如果你认为所有检索到的上下文都与问题无关，请返回空列表并将答案设置为UNKNOWN。
注意：
1、输出必须是json格式，只输出json格式内容，不需要带上解释
2、返回格式参考下面示例：

问题:
谁是《Hello Love》的演唱者？

上下文:
{'idx': 0,
 'content': '"Hello Love"是汉克·斯诺(Hank Snow)1974年的单曲。"Hello Love"是斯诺在美国乡村单曲榜上的第七首也是最后一首冠军单曲，也是他十二年来的第一首冠军单曲。这首单曲在榜首停留了一周，总共在榜上停留了十周。',
}
    
{'idx': 1,
   'content': '"Your Love Is a Song"是由另类摇滚乐队Switchfoot创作和录制的。它首先作为单曲在澳大利亚的iTunes商店发布，成为该乐队第七张录音室专辑"Hello Hurricane"的第三首电台单曲。'
}
    
{'idx': 2,
   'content': '"Will to Love"是尼尔·杨(Neil Young)创作的一首歌曲，首次收录在他1977年的专辑"American Stars \'N Bars"中。"Will to Love"发行了宣传单曲，B面是"Cortez the Killer"的现场演出版本。'
}
    
答案:
{
  "context": [0],
  "answer": "汉克·斯诺(Hank Snow)"
}

    
问题:
哪个州在田纳西州的东边？
    
上下文:
{'idx': 0,
   'content': '2013年，Ulta在美国开设了125家门店，使其门店总数达到675家。他们还宣布计划在2014年底前再开设100家门店。截至2018年8月4日，Ulta在49个州和哥伦比亚特区经营着1,124家门店。大部分Ulta Beauty门店位于东海岸地区，不过加利福尼亚州也有大量公司自营门店。',    
}
    
{'idx': 1,
   'content': '她出生并成长在瑞典斯德哥尔摩的索伦图纳，但多年来一直居住在哥德堡。玛雅通过安妮卡·诺林的乐队Hello Saferide而为人所知，她在其中担任和声歌手。她的独唱生涯始于2007年初，当时歌曲"And I Found This Boy"开始在瑞典电台大量播放。这首单曲之后发行了专辑"Though, I\'m Just Me"和单曲"Gothenburg"。2007年夏天，她在瑞典各地巡演，参加了Allsång på Skansen、Hultsfredsfestivalen、Peace & Love和Arvika Festival等演出。2010年，她首次发行瑞典语材料，推出了EP"Dröm bort mig igen"。',    
}
    
{'idx': 2,
   'content': 'Publix Super Markets, Inc.，通常被称为Publix，是一家员工持股的美国连锁超市，总部位于佛罗里达州莱克兰。由乔治·W·詹金斯于1930年创立，Publix是一家完全由现任和前任员工拥有的私人公司。它被认为是世界上最大的员工持股公司。Publix在美国东南部运营，在佛罗里达州(785家)、乔治亚州(186家)、阿拉巴马州(68家)、南卡罗来纳州(58家)、田纳西州(42家)、北卡罗来纳州(35家)和弗吉尼亚州(8家)都有门店。',    
}
    
答案:
{
  "context": [],
  "answer": "UNKNOWN"
}
"""

    def build_prompt(self, variables: Dict) -> str:
        question = variables["question"]
        context = variables["context"]

        context = "\n".join([str(x) for x in context])

        if self.language == "zh":
            return f"{self.template_zh}\n问题:\n{question}\n上下文:\n{context}"
        else:
            return f"{self.template_en}\nQuestion:\n{question}\nContext:\n{context}"

    def parse_response(self, rsp: str, **kwargs):
        if self.language == "zh":
            if isinstance(rsp, str) and "答案:" in rsp:
                response = rsp.split("答案:")[1]
            else:
                response = rsp
        else:
            if isinstance(rsp, str) and "Answer:" in rsp:
                response = rsp.split("Answer:")[1]
            else:
                response = rsp
        if isinstance(response, str):
            response = json.loads(response)

        if isinstance(response, list):
            response = response[0]
        if not isinstance(response, dict):
            raise ValueError(f"response should be a dict, but got: {response}")
        if "output" in response:
            response = response["output"]
        return response
