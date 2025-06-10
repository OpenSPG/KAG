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
The Question field is the user's question, and Context is a batch of articles retrieved from the knowledge base that may contain the answer to the question. Please carefully analyze the question and each context, and return up to 5 contexts that may contain the answer to the question, and answer the question. If you think all the retrieved contexts are irrelevant to the question, return an empty list and set the answer to UNKNOWN. The return format refers to the example：

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

    def build_prompt(self, variables: Dict) -> str:
        question = variables["question"]
        context = variables["context"]
        context = "\n".join([str(x) for x in context])
        return f"{self.template_en}\nQuestion:\n{question}\nContext:\n{context}"

    def parse_response(self, response: str, **kwargs):
        if isinstance(response, str) and "Answer:" in response:
            response = response.split("Answer:")[1]
        if isinstance(response, str):
            response = json.loads(response)

        if isinstance(response, list):
            response = response[0]
        if not isinstance(response, dict):
            raise ValueError(f"response should be a dict, but got: {response}")
        if "output" in response:
            response = response["output"]
        return response
