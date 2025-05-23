import re
from typing import List
import logging
import ast

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("bird_return_column_generator")
class BirdReturnColumnRespGenerator(PromptABC):
    template_zh = """
### 任务
基于给定的问题和schema，只给出回答问题的最终答案的最小字段集合,字段必须包含所属的实体名称。

### 问题
$question

### 图schema
```
$schema
```

### 尝试历史
$history

### 输出格式
输出你的思考过程,强调下:只给出回答问题的最终答案必需的最小字段集合,用数组的形式返回. 
注意: 最终答案请务必遵守下面的原则: 
    1): 不返回解决问题过程中用到的过滤条件字段
    2): 不返回与回答问题的最终答案的任何额外字段
    3): 如果是统计类问题,则返回count/avg/max等函数+(实体.实体属性)
    4): evidence的信息作为参考,不属于问题的部分
```return_column
结果return_column语句
```
""".strip()
    template_en = template_zh

    @property
    def template_variables(self) -> List[str]:
        return ["question", "schema", "history"]

    def parse_response(self, response: str, **kwargs):
        print("abc is here......")
        return self.parse_cypher(response)

    @staticmethod
    def parse_cypher(response):
        """
        解析LLM返回的cypher
        """
        pattern = r"```return_column\s*(.*?)\s*```"
        matches = re.findall(pattern, response, re.DOTALL)
        column_mapping = {}
        for match in matches:
            match = match.strip()
            parsed_data = ast.literal_eval(match)
            for item in parsed_data:
                if "." in item:
                    entity_name, column_name = item.split(".", 1)
                    if entity_name in column_mapping.keys():
                        column_mapping[entity_name].append(column_name)
                    else:
                        column_mapping[entity_name] = []
                        column_mapping[entity_name].append(column_name)
        return column_mapping

    def is_json_format(self):
        return False
