import re
import json
from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_question_output_check")
class QuestionOutputPrompt(PromptABC):
    template_zh = """
### 任务
你的任务是判断返回的属性列表与给出的问题是否匹配。

### 注意
1. 你不允许回答该问题，而是分析这个问题应该返回哪些字段。
2. 返回字段或属性必须在图schema中存在。
3. 根据你的分析，判断计划返回的属性列表是否正确。
4. 如果给出的属性列表不正确，给出原因。

### 问题
$question

### 计划返回的属性列表
$return_property_list

### 图schema
```
$schema
```

### 输出
先输出你的思考过程，最后以json返回结果。
```json
{
  "provided_output_list_correct": "true/false",
  "should_output_list": [
    "entityA.property1",
    "entityB.property2",
    "edgeC.property3"
  ],
  "reason": "Give reasons why is it incorrect?"
}
```
""".strip()

    template_en = template_zh

    @property
    def template_variables(self) -> List[str]:
        return ["question", "schema", "return_property_list"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        return self.parse_result_json(response)

    def process_quotes(self, input_str):
        """
        处理json格式中有换行的问题
        """

        def replace_newlines(match):
            # 获取引号中的内容
            content = match.group(1)
            # 将换行符替换为转义的 \n
            processed_content = content.replace("\n", r"\n")
            # 返回替换后的内容，用引号包裹
            return f'"{processed_content}"'

        # 使用正则匹配引号对（支持双引号）
        pattern = r'"(.*?)"'
        # 替换所有引号内的内容
        result = re.sub(pattern, replace_newlines, input_str, flags=re.DOTALL)
        return result

    def parse_result_json(self, response):
        """
        解析LLM返回的json
        """
        pattern = r"```json\s*(.*?)\s*```"
        matches = re.findall(pattern, response, re.DOTALL)
        valid_jsons = []
        for match in matches:
            try:
                match = match.strip()
                parsed_json = json.loads(match)
                valid_jsons.append(parsed_json)
            except json.JSONDecodeError:
                try:
                    match = self.process_quotes(match)
                    parsed_json = json.loads(match)
                    valid_jsons.append(parsed_json)
                except json.JSONDecodeError:
                    print("Warning: Found invalid JSON content.")
                    continue
        if len(valid_jsons) == 0:
            return None
        json_rst = valid_jsons[-1]
        return json_rst

    def is_json_format(self):
        return False
