import re
import logging
import json
from typing import List, Optional

from kag.interface import PromptABC


@PromptABC.register("default_base_schema")
class BasehSchemaPrompt(PromptABC):
    """
    extract table context
    """

    template_zh = """
### 任务
你是一个知识图谱建模专家，你的任务是分析给出的表，识别表属于关系表还是实体表，并输出属性列表。

### 要求
1. 输入schema包括目标表，及库中其他表，你只需要专注于识别目标表类型和属性。
2. 关系表需要满足：主键不被其他表引用；表包含这样两列，这两列分别以外键关联到其他表的主键。
3. 只有在你非常肯定该表是边关系表时，输出该表为边关系表，否则输出为实体表。
4. 先输出你的思考过程，再以json总结最终结果。
5. 输出中文属性描述信息。

### 输出
思考过程...略
关系表返回样例
```json
{
  "is_relation_table": "true",
  "edge_type": "使用一个词准确的表达关系类型，使subject_entity + edge_type + object_entity是一个易于理解的主谓宾短语",
  "subject_table": "关系主语，输出表名",
  "object_table": "关系宾语，输出表名",
  "subject_column": "主语对应的列名",
  "object_column": "宾语对应的列名",
  "property_list": {
    "属性名(继承自列名)": "总结出简洁准确的属性描述信息"
  }
}
```
实体表返回样例
```json
{
  "is_relation_table": "false",
  "entity_name_column": "实体唯一标识，可理解可索引的列",
  "property_list": {
    "属性名(继承自列名)": "参考列注释总结出简洁准确的属性描述信息"
  }
}
```

### 当前处理的表
$table_schema
### 库中其他表
$other_tables_schema
""".strip()

    template_en = template_zh

    def __init__(self, language: Optional[str] = "en", **kwargs):
        super().__init__(language, **kwargs)

    @property
    def template_variables(self) -> List[str]:
        return ["table_schema", "other_tables_schema"]

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
