from typing import Set, Dict


class TableInfo:
    def __init__(self, table_name:str):
        self.table_name = table_name
        # tablename keywords and colloquial
        self.table_name_colloquial = {}
        # key:2-1,value: TableCell
        self.cell_dict = {}

        # key: header or index row string
        # value: sub item, row string
        self.sub_item_dict = {}

        self.sacle = None
        self.unit = None
        self.context_keywords = {}



class TableCell:
    def __init__(
        self,
        desc: str = None,
        row_keywords: Dict = None,
    ):
        # xxx shows yyy is zzz
        self.desc = desc
        # key: header or index row string
        # value is dict[str, set()], value_key is splited_keyword, value_set is colloquial
        self.row_keywords = {} if row_keywords is None else row_keywords

        self.value = None
