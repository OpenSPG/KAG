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
    2): 把问题中的核心词汇尽量多的提取出来，并通过核心词汇相似来召回neo4j图数据库中的内容
    3): 产出的cypher中涉及到的所有实体和关系及对应的属性必须来自schema中给定的,不要私自修改schema中的内容. 目前实体有: RiskSentimentsEventQA.Event
    4): 从主要是的字段中进行条件判断,如: eventContent,objName等,并谨慎使用AND条件.
    5): 用`符号把实体类型(如: RiskSentimentsEventQA.Event)包裹起来,注意,不要包裹Cypher中的别名,而是具体的实体类型.
    6): 产出Cypher中每次最多召回10条内容,避免返回整个实体,而是按实体的相关性字段进行返回.


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
