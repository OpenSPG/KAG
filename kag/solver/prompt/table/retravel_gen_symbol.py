import json
import re
from string import Template
from typing import List
import logging

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class RetrivalGenerateSymbolPrompt(PromptOp):
    template_zh = """
# Task
根据给出的问题，结合schema信息，生成图数据查询过程。

# Instruction
根据要查询的数据，先确定数据所在的Table，可以一次查询多张Table的数据。
从Table出发，查找数据所在的TableRow或TableColumn，最后找到TableCell值。
如果可能有多重查询路径，全部输出出来。
如果需要查询TableRow之间的上下位关系，使用subitem关系。
如果无法回答，返回: I don't know.

# output format
输出json格式，内容是路径查询列表，每个路径包含desc，以及需要查询的三元组spo。
spo中必须包含var（变量名），type（实体或关系类型），link（目标实体或关系的名称，在图数据上进行链指）

# Schema and data example
```json
{
  "entities": [
    {
      "name": "Table",
      "properties": ["name", "desc"],
      "relationships": [
        {"p": "containRow"   , "s": "Table", "o": "TableRow"   },
        {"p": "containColumn", "s": "Table", "o": "TableColumn"}
      ]
    },
    {
      "name": "TableRow",
      "properties": ["name", "desc"],
      "relationships": [
        {"p": "containCell", "s": "TableRow", "o": "TableCell"},
        {"p": "partOf"     , "s": "TableRow", "o": "Table"    },
        {"p": "subitem"    , "s": "TableRow", "o": "TableRow" }
      ]
    },
    {
      "name": "TableColumn",
      "properties": ["name", "desc"],
      "relationships": [
        {"p": "containCell", "s": "TableColumn", "o": "TableCell"},
        {"p": "partOf"     , "s": "TableColumn", "o": "Table"    }
      ]
    },
    {
      "name": "TableCell",
      "properties": ["name", "value", "scale", "unit"],
      "relationships": [
        {"p": "partOfTableRow"   , "s": "TableCell", "o": "TableRow"   },
        {"p": "partOfTableColumn", "s": "TableCell", "o": "TableColumn"},
        {"p": "partOfTable"      , "s": "TableCell", "o": "Table"      }
      ]
    },
    {
      "name": "TableKeyword",
      "properties": [ {"name": "name", "type": "string"} ],
      "relationships": [
        {"p": "keyword", "s": "TableKeyword", "o": "Table"      },
        {"p": "keyword", "s": "TableKeyword", "o": "TableColumn"}
      ]
    }
  ],
  "data_examples": [
    {
      "s": {"id": "阿里巴巴2025财年上半年财报-营业收入明细表", "type": "Table"},
      "p": "containRow",
      "o": {"id": "阿里巴巴2025财年上半年财报-营业收入明细表-淘天集团", "type": "TableRow"}
    },
    {
      "s": {"id": "阿里巴巴2025财年上半年财报-营业收入明细表", "type": "Table"},
      "p": "containRow",
      "o": {"id": "阿里巴巴2025财年上半年财报-营业收入明细表-中国零售商业", "type": "TableRow"}
    },
    {
      "s": {"id": "阿里巴巴2025财年上半年财报-营业收入明细表-淘天集团", "type": "TableRow"},
      "p": "subitem",
      "o": {"id": "阿里巴巴2025财年上半年财报-营业收入明细表-中国零售商业", "type": "TableRow"}
    },
    {
      "s": {"id": "阿里巴巴2025财年上半年财报-营业收入明细表", "type": "Table"},
      "p": "containColumn",
      "o": {
        "id"  : "阿里巴巴2025财年上半年财报-营业收入明细表-截至9月30日止6个月-2024-人民币",
        "type": "TableColumn"
      }
    },
    {
      "s": {"id": "阿里巴巴2025财年上半年财报-营业收入明细表-淘天集团", "type": "TableRow"},
      "p": "containCell",
      "o": {
        "id"   : "阿里巴巴2025财年上半年财报-营业收入明细表-淘天集团-截至9月30日止6个月-2023-人民币",
        "type" : "TableCell"                                        ,
        "value": "212,607"                                          ,
        "scale": "百万"                                               ,
        "unit" : "人民币"
      }
    },
    {
      "s": {
        "id"   : "阿里巴巴2025财年上半年财报-营业收入明细表-淘天集团-截至9月30日止6个月-2023-人民币",
        "type" : "TableCell"                                        ,
        "value": "212,607"                                          ,
        "scale": "百万"                                               ,
        "unit" : "人民币"
      },
      "p": "partOfTableRow",
      "o": {"id": "阿里巴巴2025财年上半年财报-营业收入明细表-中国零售商业", "type": "TableRow"}
    },
    {
      "s": {"id": "阿里巴巴", "type": "TableKeyword"},
      "p": "keyword",
      "o": {"id": "阿里巴巴2025财年上半年财报-营业收入明细表", "type": "Table"}
    },
    {
      "s": {"id": "人民币", "type": "TableKeyword"},
      "p": "keyword",
      "o": {
        "id"  : "阿里巴巴2025财年上半年财报-营业收入明细表-截至9月30日止6个月-2023-人民币",
        "type": "TableColumn"
      }
    }
  ]
}
```

# Examples
## 查具体数值
### input
查找阿里巴巴2024年截至9月30日6个月的收入是多少？
### output
```json
[
  {
    "desc": "找到阿里巴巴2024年截至9月30日6个月的收入内容",
    "s": {
      "var": "s1",
      "type": "Table",
      "link": ["阿里巴巴营收明细表", "阿里巴巴业绩概要表"]
    },
    "p": {
      "var": "p1",
      "type": "containRow"
    },
    "o": {
      "var": "o1",
      "type": "TableRow",
      "link": [
        "营业收入",
        "营收",
        "收入"
      ]
    }
  },
  {
    "desc": "通过阿里巴巴2024年截至9月30日6个月的收入内容，获取到具体数值",
    "s": {
      "var": "o1"
    },
    "p": {
      "var": "p2",
      "type": "containCell"
    },
    "o": {
      "var": "o2",
      "type": "TableCell",
      "link": "2024年截至9月30日6个月"
    }
  }
]
```

## 查构成，查子项目
### input
召回阿里巴巴2024年截至9月30日六个月经营利润的构成(详情，子项目)
### output
```json
[
  {
    "desc": "查找阿里巴巴经营利润信息",
    "s": {
      "var": "s1",
      "type": "Table",
      "link": ["阿里巴巴经营利润详情表"]
    },
    "p": {
      "var": "p1",
      "type": "containRow"
    },
    "o": {
      "var": "o1",
      "type": "TableRow",
      "link": [
        "经营利润"
      ]
    }
  },
  {
    "desc": "根据经营利润信息，查找经营利润的子项目信息",
    "s": {
      "var": "o1"
    },
    "p": {
      "var": "p2",
      "type": "subitem"
    },
    "o": {
      "var": "o2",
      "type": "TableRow"
    }
  },
  {
    "desc": "通过查询到的所有子项目(多行数据)，查找每行数据上的2024年截至9月30日6个月具体内容",
    "s": {
      "var": "o2"
    },
    "p": {
      "var": "p3",
      "type": "containCell"
    },
    "o": {
      "var": "o3",
      "type": "TableCell",
      "link": [
        "2024年截至9月30日6个月"
      ]
    }
  }
]
```

# real input
$input

# tables we have
$table_names

# your output
"""
    template_en = template_zh

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["input", "table_names"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        try:
            return json.loads(rsp)
        except ValueError:
            pattern = r"```json(.*?)```"
            matches = re.findall(pattern, rsp, re.DOTALL)
            cleaned_matches = [match.strip() for match in matches]
            if len(cleaned_matches) > 0:
                rsp = json.loads(cleaned_matches[0])
        return rsp
