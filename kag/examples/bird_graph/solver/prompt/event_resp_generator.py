import re
from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("event_resp_generator")
class EventRespGenerator(PromptABC):
    template_zh = """
### 任务
基于给定的问题和schema,请严格遵守如下规则,并产出Cypher。: 
    1): 尽量用CONTAINS语法来召回尽量多的相关内容，少用 a = '条件a的值' 的条件来硬匹配。 如: e.eventContent contains '泰康人寿' 表示用事件内容字段中包含中泰康人寿关键字的事件. 
    2): 把问题中的核心词汇提取出来，并通过核心词汇相似来召回neo4j图数据库中的内容
    3): 产出的cypher中涉及到的所有实体和关系及对应的属性必须来自schema中给定的,不要私自修改schema中的内容.
    4): where条件中in的语法是 ['a','b','c'],包含in语法时,务必遵守该格式.
    5): 用`符号把实体类型包裹起来.


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
