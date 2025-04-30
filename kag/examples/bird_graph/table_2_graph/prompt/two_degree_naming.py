import re
import logging
import json
from typing import List, Optional

from kag.interface import PromptABC


@PromptABC.register("default_two_degree_edge_naming")
class TwoDegreeEdgeNamingPrompt(PromptABC):
    """
    extract table context
    """

    template_zh = """
### 任务
你是一个知识图谱建模专家，你的任务是为概念关系命名。

### 要求
1. 理解输入的两张表schema以及表之间关联的两列，判断该关联关系是否合理。如果不合理按照输出格式，输出reasonable=false，其他字段为空。
2. 如何合理，为两张表之间的列命名，要求能准确表达中间实体的类型。输出到entity_type中。
2. 要求 table_1 + edge_type_1 + entity_type 能构成通顺的主谓宾短语。
3. 要求 table_2 + edge_type_2 + entity_type 能构成通顺的主谓宾短语。
4. 使用json格式输出。

### 输出格式
```json
{
  "reasonable": "true/false",
  "entity_type": "中间实体的名称",
  "edge_type_1": "表1与中间实体的关系",
  "edge_type_2": "表2与中间实体的关系",
}
```

### 关联关系
$map_info
### Table_1
$table_schema_1
### Table_2
$table_schema_2
""".strip()

    template_en = template_zh

    def __init__(self, language: Optional[str] = "en", **kwargs):
        super().__init__(language, **kwargs)

    @property
    def template_variables(self) -> List[str]:
        return ["map_info", "table_schema_1", "table_schema_2"]

    def parse_response(self, response: str, **kwargs):
        return self.get_json_from_response(response)

    def get_json_from_response(self, response):
        """
        解析LLM返回的表schema结果
        """
        pattern = r"```json\s*(.*?)\s*```"
        matches = re.findall(pattern, response, re.DOTALL)
        valid_jsons = []
        for match in matches:
            try:
                parsed_json = json.loads(match.strip())
                valid_jsons.append(parsed_json)
            except json.JSONDecodeError:
                print("Warning: Found invalid JSON content.")
                continue
        if len(valid_jsons) == 0:
            return None
        graph_schema = valid_jsons[-1]
        return graph_schema
