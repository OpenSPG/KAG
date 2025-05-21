import re
from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_fix_cypher")
class FixCypherTestPrompt(PromptABC):
    template_zh = """
### 任务
基于给定的问题和schema，修正cypher。

### 注意
1. 结合schema分析问题，从schema中选出问题需要返回的属性列表。基于此判断cypher返回是否符合问题需要的属性列表。
2. 如果cypher中有order by子句，对order by的字段添加is not null约束，因为null会影响排序结果，导致错误。
3. 如果没有上述问题，返回原cypher即可。

### 问题
$question

### 图schema
```
$schema
```

### cypher
```cypher
$cypher
```

### 输出格式
输出你的思考过程，最后返回cypher。
```cypher
结果cypher语句
```
""".strip()
    template_en = template_zh

    @property
    def template_variables(self) -> List[str]:
        return ["question", "schema", "cypher"]

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
