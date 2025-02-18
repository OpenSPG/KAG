from typing import Dict


class TableCellDesc:
    def __init__(self):
        self.row_desc_list = []
        self.column_desc_list = []
        self.desc_dict = {}


class TableDefaultInfo:
    def __init__(self, name, desc, keywords, table_type):
        self.name = name
        self.desc = desc
        self.keywords = keywords
        self.table_type = table_type


class TableCellValue:
    def __init__(
        self,
        value: str,
        desc: str = None,
        row_name: str = None,
        column_name: str = None,
        scale: str = None,
        unit: str = None,
    ):
        self.value = value
        self.desc = desc
        self.row_name = row_name
        self.column_name = column_name
        self.scale = scale
        self.unit = unit
