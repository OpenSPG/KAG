import re
import json
from typing import List
import logging

from kag.interface import PromptABC, Task

logger = logging.getLogger(__name__)


@PromptABC.register("default_bird_plan_prompt")
class BirdPlanPrompt(PromptABC):
    template_zh = """
### 任务
你是一个图数据数据分析专家，你的任务是将复杂查询问题拆解为子问题。
子问题会被翻译为Cypher并执行，以确认子问题得到正确的Cypher。

### 注意
1. 你不需要回答该问题，而是产出解决问题的步骤和方法。
2. 结合图schema信息，来拆分子问题。保证子问题使用的图数据度数可控（不能太深，最好只用一度，围绕一个实体）。

### 待解决问题
$query

### 执行器列表
$executors

### 图schema
```
$schema
```

### 输出
输出你的思考过程，最后以json格式返回子问题及依赖关系。
```json
{
  "sub_question_1": {
    "content": "子问题1内容",
    "dependence": [],
    "executor": "执行器列表中的某一个"
  },
  "sub_question_2": {
    "content": "子问题2内容",
    "dependence": ["sub_question_1"],
    "executor": "执行器列表中的某一个"
  }
}
```
""".strip()

    template_en = template_zh

    @property
    def template_variables(self) -> List[str]:
        return ["query", "schema", "executors"]

    def parse_response(self, response: str, **kwargs):
        response = self.parse_result_json(response)
        response = self.convert_task_json(response)
        return Task.create_tasks_from_dag(response)

    def convert_task_json(self, task_json):
        rst = {}
        for k, v in task_json.items():
            rst[k] = {
                "executor": v["executor"],
                "dependent_task_ids": v["dependence"],
                "arguments": {"query": v["content"]},
            }
        return rst

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
