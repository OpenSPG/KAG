import re
import logging
import json
from typing import List, Optional

from kag.interface import PromptABC


@PromptABC.register("default_one_degree_edge_naming")
class OneDegreeEdgeNamingPrompt(PromptABC):
    """
    extract table context
    """

    template_zh = """
### 任务
你是一个知识图谱建模专家，你的任务是为外键关系命名。

### 要求
1. 理解输入的表schema和外键关系，判断外键关系是否合理。如果不合理按照输出格式，输出reasonable=false，其他字段为空。
2. 如何合理，为外键取一个简洁易于理解的名称，填入edge_type。
2. 要求 subject_table + edge_type + object_table 能构成通顺的主谓宾短语。
3. 先输出你的思考过程，再使用json格式总结输出。

### 输出格式
```json
{
  "reasonable": "true/false",
  "edge_type": "边关系类型",
  "subject_table": "关系主语，输出表名",
  "object_table": "关系宾语，输出表名",
  "subject_column": "主语对应的列名",
  "object_column": "宾语对应的列名",
}
```

### 外键
$foreign_key
### 表schema
$table_schema
""".strip()

    template_en = template_zh

    def __init__(self, language: Optional[str] = "en", **kwargs):
        super().__init__(language, **kwargs)

    @property
    def template_variables(self) -> List[str]:
        return ["foreign_key", "table_schema"]

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
