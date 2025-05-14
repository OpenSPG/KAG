import re
from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_bird_resp_generator")
class BirdRespGenerator(PromptABC):
    template_zh = """
### 任务
基于给定的问题和schema，产出Cypher。

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
