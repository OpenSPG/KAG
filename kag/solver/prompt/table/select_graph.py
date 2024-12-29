import re
from string import Template
from typing import List
import logging

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class SelectDocsPrompt(PromptOp):
    template_zh = """
# instruction
基于给定的信息和图查询结果，选择与问题最相关的实体name。

# output format
json格式

# example
## example question
召回阿里巴巴2024年-截至9月30日止六个月的经营成本和费用总额

## example graph query plan
```json
[{"desc": "通过表查询成本和费用明细表，link表示通过给定的名称链指到图上的实体", "s": {"var": "s1", "type": "Table", "link": "阿里巴巴2025财年度中期报告成本和费用明细"}, "p": {"var": "p1", "type": "containRow"}, "o": {"var": "o1", "type": "TableRow", "link": ["经营成本和费用总额"]}}, {"desc": "通过上一步查询到的经营成本和费用总额那一行数据，查询具体的TableCell", "s": {"var": "o1"}, "p": {"var": "p2", "type": "containCell"}, "o": {"var": "o2", "type": "TableCell", "link": "2024年截至9月30日止六个月"}}]
```
## example graph query result
```json
{"s1": [{"prop": {"origin_prop_map": {"name": "阿里巴巴2025财年度中期报告成本和费用明细", "id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb", "desc": "下表载列于所示期间内我们按功能划分的成本及费用、股权激励费用及不含股权激励费用的成本及费用明细"}, "extend_prop_map": {}}, "biz_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb", "name": "阿里巴巴2025财年度中期报告成本和费用明细", "description": "", "type": "FinState.Table", "type_zh": "表格"}], "p1": [{"prop": {"origin_prop_map": {}, "extend_prop_map": {}}, "from_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb", "end_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-row-0", "from_entity_name": "阿里巴巴2025财年度中期报告成本和费用明细", "from_type": "Table", "end_entity_name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额", "end_type": "TableRow", "type": "containRow"}], "o1": [{"prop": {"origin_prop_map": {"name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额", "row_name": "成本和费用总额", "id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-row-0", "desc": "下表载列于所示期间内我们按功能划分的成本及费用、股权激励费用及不含股权激励费用的成本及费用明细"}, "extend_prop_map": {}}, "biz_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-row-0", "name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额", "description": "", "type": "FinState.TableRow", "type_zh": "表格行"}], "p2": [{"prop": {"origin_prop_map": {}, "extend_prop_map": {}}, "from_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-row-0", "end_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-0-0", "from_entity_name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额", "from_type": "TableRow", "end_entity_name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额-2023年-截至9月30日止六个月-人民币", "end_type": "TableCell", "type": "containCell"}, {"prop": {"origin_prop_map": {}, "extend_prop_map": {}}, "from_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-row-0", "end_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-0-2", "from_entity_name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额", "from_type": "TableRow", "end_entity_name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额-2024年-截至9月30日止六个月-人民币", "end_type": "TableCell", "type": "containCell"}, {"prop": {"origin_prop_map": {}, "extend_prop_map": {}}, "from_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-row-0", "end_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-0-3", "from_entity_name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额", "from_type": "TableRow", "end_entity_name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额-2024年-截至9月30日止六个月-美元", "end_type": "TableCell", "type": "containCell"}], "o2": [{"prop": {"origin_prop_map": {"unit": [], "row_name": "成本和费用总额", "name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额-2023年-截至9月30日止六个月-人民币", "scale": "百万", "col_name": "2023年-截至9月30日止六个月-人民币", "id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-0-0", "value": "382872", "desc": "[阿里巴巴2025财年度中期报告成本和费用明细]cell[0-0] shows 成本和费用总额 of 2023年-截至9月30日止六个月-人民币 is 382872(百万)"}, "extend_prop_map": {}}, "biz_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-0-0", "name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额-2023年-截至9月30日止六个月-人民币", "description": "", "type": "FinState.TableCell", "type_zh": "单元格"}, {"prop": {"origin_prop_map": {"unit": [], "row_name": "成本和费用总额", "name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额-2024年-截至9月30日止六个月-美元", "scale": "百万", "col_name": "2024年-截至9月30日止六个月-美元", "id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-0-3", "value": "58332", "desc": "[阿里巴巴2025财年度中期报告成本和费用明细]cell[0-3] shows 成本和费用总额 of 2024年-截至9月30日止六个月-美元 is 58332(百万)"}, "extend_prop_map": {}}, "biz_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-0-3", "name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额-2024年-截至9月30日止六个月-美元", "description": "", "type": "FinState.TableCell", "type_zh": "单元格"}, {"prop": {"origin_prop_map": {"unit": [], "row_name": "成本和费用总额", "name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额-2024年-截至9月30日止六个月-人民币", "scale": "百万", "col_name": "2024年-截至9月30日止六个月-人民币", "id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-0-2", "value": "409355", "desc": "[阿里巴巴2025财年度中期报告成本和费用明细]cell[0-2] shows 成本和费用总额 of 2024年-截至9月30日止六个月-人民币 is 409355(百万)"}, "extend_prop_map": {}}, "biz_id": "797efaca3ad72280029bae9e0bd8fd594aa633bf077ed3b3f1805251809a07eb-0-2", "name": "阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额-2024年-截至9月30日止六个月-人民币", "description": "", "type": "FinState.TableCell", "type_zh": "单元格"}]}
```

## example output
与问题最相关的是FinState.TableCell：阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额-2024年-截至9月30日止六个月-人民币
```json
["阿里巴巴2025财年度中期报告成本和费用明细-成本和费用总额-2024年-截至9月30日止六个月-人民币"]
```

# question
$question

# graph query plan
```json
$graph_query_plan
```

# graph query result
```json
$graph_query_restult
```
# your output
"""
    template_en = template_zh

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["question", "graph_query_plan", "graph_query_result"]

    def parse_response(self, response: str, **kwargs):
        return response
