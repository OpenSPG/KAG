import re
from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_nl2cypher")
class Nl2CypherPrompt(PromptABC):
    template_zh = """
### 任务
你是一个Cypher语言专家，你的任务是解决复杂查询任务中的一个子问题，为这个子问题生成正确的Cypher语句。

### 注意
1. 你解决的是子问题，而不是父问题。生成的Cypher解决的是子问题。
2. 生成的Cypher会被执行，以判断Cypher的正确性。如果执行失败，会有错误信息。这些都会被记录在尝试历史中。
3. 注意观察之前的尝试，如果无结果或错误，再仔细理解图schema以及父子问题，重新生成新Cypher。
4. 你生成的Cypher必须不同于尝试历史记录中的Cypher，使用新的思路进行生成。

### 当前子问题
$question

### 图schema
```
$schema
```

### 父问题
$goal

### 前置子问题的答案
$old_cypher

### 尝试历史记录
$history

### 输出
输出你的思考过程，最后返回cypher，使用markdown格式。
```cypher
结果cypher语句
```
""".strip()

    template_en = template_zh

    @property
    def template_variables(self) -> List[str]:
        return ["question", "schema", "old_cypher", "goal", "history"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
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
            return None
        cypher = valid_list[-1]
        return cypher

    def is_json_format(self):
        return False
