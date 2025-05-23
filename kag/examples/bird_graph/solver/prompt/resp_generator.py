import re
from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_bird_resp_generator")
class BirdRespGenerator(PromptABC):
    template_zh = """
### 任务
基于给定的问题和schema,请严格遵守如下规则,并产出Cypher。: 
    1): 所有的字段名字中包含' '的都必须用``把字段包起来
    2): schema中有edge_type字段的为边类型,{"s": "frpm","edge_type": "hasfrpmdata", "o": "schools"} 
        其中s为起点、edge_type为边类型，o为终点. 生成的cypher应为: (f:frpm)-[h:hasfrpmdata]->(s:schools),注意cypher语句方向的正确性.
    3): 生成cypher时请参考evidence的信息，它提供给你在回答问题所需的知识点,但注意:evidence不是问题本身.
    4): 问题中没有明确去重的都不要在cypher中加 DISTINCT
    5): where条件中in的语法是 ['a','b','c'],包含in语法时,务必遵守该格式.
    6): return 只返回回答问题的最终答案必需的最小字段集合,不要返回与问题最终答案无关的任何额外的字段,包括一些过滤字段等.

### 问题
$question

### 图schema
```
$schema
```

### 尝试历史
$history

### 输出格式
输出你的思考过程，最后返回cypher。
```cypher
结果cypher语句
```
""".strip()
    template_en = template_zh

    @property
    def template_variables(self) -> List[str]:
        return ["question", "schema", "history"]

    def parse_response(self, response: str, **kwargs):
        return self.parse_cypher(response)

    def parse_cypher(self, response):
        """
        解析LLM返回的cypher
        """
        pattern = r"```cypher\s*(.*?)\s*```"
        matches = re.findall(pattern, response, re.DOTALL)
        valid_list = []
        for match in matches:
            match = match.strip()
            valid_list.append(match)
        if len(valid_list) == 0:
            return ""
        cypher = valid_list[-1]
        return cypher

    def is_json_format(self):
        return False
