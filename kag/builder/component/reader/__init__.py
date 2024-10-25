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

from kag.builder.component.reader.csv_reader import CSVReader
from kag.builder.component.reader.pdf_reader import PDFReader
from kag.builder.component.reader.json_reader import JSONReader
from kag.builder.component.reader.markdown_reader import MarkDownReader
from kag.builder.component.reader.docx_reader import DocxReader
from kag.builder.component.reader.txt_reader import TXTReader
from kag.builder.component.reader.dataset_reader import HotpotqaCorpusReader, TwowikiCorpusReader, MusiqueCorpusReader
from kag.builder.component.reader.yuque_reader import YuqueReader

__all__ = [
    "TXTReader",
    "PDFReader",
    "MarkDownReader",
    "JSONReader",
    "HotpotqaCorpusReader",
    "MusiqueCorpusReader",
    "TwowikiCorpusReader",
    "YuqueReader",
    "CSVReader",
    "DocxReader",
]
