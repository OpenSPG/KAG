# -*- coding: utf-8 -*-
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.


class TableCellDesc:
    """
    information for table cell description
    """

    def __init__(self):
        self.row_desc_list = []
        self.column_desc_list = []
        self.desc_dict = {}


class TableDefaultInfo:
    """
    Default parsing results for table data
    """

    def __init__(self, name, desc, keywords, table_type):
        self.name = name
        self.desc = desc
        self.keywords = keywords
        self.table_type = table_type


class TableCellValue:
    """
    The content of the cell in the table
    """

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
