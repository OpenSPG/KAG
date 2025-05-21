import re
import logging
import json
from typing import List, Optional

from kag.interface import PromptABC


@PromptABC.register("default_one_degree_edge")
class OneDegreeEdgePrompt(PromptABC):
    """
    extract table context
    """

    template_zh = """
### 任务
你是一个知识图谱建模专家，你的任务是分析当前表schema，对表中的每一列按照流程处理。

### 列处理流程
1. 如果该列可以关联到其他表的主键，输出type=foreign_key,target_column=table.column
2. 如果该列可能与其他表的某一列有相等的可能，并且通过中间列关联后是有意义的。这时输出type=concept,target_column=table.column
  - order.amount和trans.amount等浮点数类型的列之间关联一般是无意义的。
  - order.type和acount.type虽然列名相同类型相同，但是值不可能相等，且关联后无意义。
  - date类型关联后意义在于同一天同一时刻，一般也是无意义的。
3. 该列与自己关联后，有意义，则输出type=concept,target_column=table.column
  - 例如：student.class列，通过class列关联，表达的是同班同学的关系，有意义。
  - 例如：trans.amount列，关联后意义是相同转账金额关系，一般没有意义。
4. 其他情况，输出type=other

### 输出
先输出你的思考过程，在按照如下json格式返回最终结果。
```json
[
{
  "column": "column_name",
  "type": "foreign_key/concept/other",
  "target_column": ["目标表和列"],
}
]
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
