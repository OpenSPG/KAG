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


class TableDefaultInfo:
    """
    Default parsing results for table data
    """

    def __init__(self, name, desc, keywords):
        self.name = name
        self.desc = desc
        self.keywords = keywords


class TableRowSummary:
    """
    Table row summary info
    """

    def __init__(self, summary, content):
        self.summary = summary
        self.content = content


class TableColSummary:
    """
    Table column summary info
    """

    def __init__(self, summary, content):
        self.summary = summary
        self.content = content
