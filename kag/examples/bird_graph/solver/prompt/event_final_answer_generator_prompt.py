import re
from typing import List
import logging
import ast

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("event_final_answer_generator")
class BirdReturnColumnRespGenerator(PromptABC):
    template_zh = """
### 任务
基于给定的问题及对应的相关内容,生成答案。尽可能多的根据给你的内容进行回答，详细一些，并输出你的思考过程. 如果给定的内容不足，你可以自行根据你知道的信息进行补充扩散..

### 问题
$question

### 相关内容
```
$content
```

### 输出格式

```return_column
结果return_column语句
```
""".strip()
    template_en = template_zh

    @property
    def template_variables(self) -> List[str]:
        return ["question", "content"]

    def parse_response(self, response: str, **kwargs):
        return self.parse_cypher(response)

    @staticmethod
    def parse_cypher(response):
        """
        解析LLM返回的cypher
        """
        pattern = r"```return_column\s*(.*?)\s*```"
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            match = match.strip()
            return match
        return matches

    def is_json_format(self):
        return False
