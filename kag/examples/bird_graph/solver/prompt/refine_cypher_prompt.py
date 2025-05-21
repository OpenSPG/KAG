import re
from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_refine_cypher")
class Nl2CypherPrompt(PromptABC):
    template_zh = """
### 任务
你是一个Cypher语言专家，你的任务是根据问题和Cypher以及Cypher的执行结果，判断Cypher是否正确。如果不正确，重写Cypher。

### 注意
1. 你生成的Cypher只需要解决当前问题，当前问题是父问题的一个子问题。如果当前问题表述不准确，可以根据父问题进行修正。
2. 尽可能参考背景知识中已有的Cypher，在其基础上进行改进。

### 当前问题
$question

### 父问题
$goal

### 图schema
```
$schema
```

### Cypher及其执行结果
```cypher
$old_cypher
```
执行结果：
```csv
$cypher_result
```

### 输出
输出你的思考过程，最后返回cypher，使用markdown格式。
如果cypher是正确的，直接输出`cypher及其执行结果可以解决当前问题`。
```cypher
结果cypher语句
```
""".strip()

    template_en = template_zh

    @property
    def template_variables(self) -> List[str]:
        return ["question", "schema", "old_cypher", "cypher_result", "goal"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        return self.parse_cypher(response)

    def parse_cypher(self, response):
        """
        解析LLM返回的cypher
        """
        if "cypher及其执行结果可以解决当前问题" in response:
            return True
        pattern = r"```cypher\s*(.*?)\s*```"
        matches = re.findall(pattern, response, re.DOTALL)
        valid_list = []
        for match in matches:
            match = match.strip()
            valid_list.append(match)
        if len(valid_list) == 0:
            return None
        cypher = valid_list[-1]
        return cypher

    def is_json_format(self):
        return False
