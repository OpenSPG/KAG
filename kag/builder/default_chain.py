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

import logging
import importlib
import os

from kag.builder.component import KGWriter
from kag.builder.component.extractor import KAGExtractor
from kag.builder.component.aligner import SemanticAligner
from kag.builder.component.splitter import LengthSplitter
from kag.common.base.chain import Chain

logger = logging.getLogger(__name__)


READER_MAPPING = {
    "csv": "kag.builder.component.reader.csv_reader.CSVReader",
    "json": "kag.builder.component.reader.json_reader.JSONReader",
    "txt": "kag.builder.component.reader.txt_reader.TXTReader",
    "pdf": "kag.builder.component.reader.pdf_reader.PDFReader",
    "docx": "kag.builder.component.reader.docx_reader.DocxReader",
    "md": "kag.builder.component.reader.markdown_reader.MarkdownReader",
}


class KAGBuilderChain(Chain):

    @property
    def input_types(self):
        return str

    @property
    def output_types(self):
        return None

    def get_reader(self, suffix: str):
        assert suffix.lower() in READER_MAPPING, f"{suffix} is not supported. Supported suffixes are: {list(READER_MAPPING.keys())}"
        reader_path = READER_MAPPING.get(suffix.lower())
        mod_path, class_name = reader_path.rsplit('.', 1)
        module = importlib.import_module(mod_path)
        reader_class = getattr(module, class_name)
        return reader_class(output_types="Chunk")

    def get_dag(self, suffix: str):
        source = self.get_reader(suffix)
        splitter = LengthSplitter()
        extractor = KAGExtractor()
        sink = KGWriter()
        if eval(os.getenv("KAG_INDEXER_WITH_SEMANTIC_HYPER_EXPAND", 'False')):
            aligner = SemanticAligner()
            chain = source >> splitter >> extractor >> aligner >> sink
        else:
            chain = source >> splitter >> extractor >> sink
        print(f"Index Builder DAG: {chain.dag.nodes}")
        return chain.dag

    def invoke(self, file_path, **kwargs):
        suffix = file_path.split(".")[-1]
        self.dag = self.get_dag(suffix)
        max_workers = kwargs.get("max_workers", 10)
        self.run(input=file_path, max_workers=max_workers)
