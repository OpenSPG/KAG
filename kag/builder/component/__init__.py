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

from kag.builder.component.extractor.kag_extractor import KAGExtractor
from kag.builder.component.extractor.spg_extractor import SPGExtractor
from kag.builder.component.aligner.kag_post_processor import KAGPostProcessorAligner
from kag.builder.component.aligner.spg_post_processor import SPGPostProcessorAligner
from kag.builder.component.mapping.spg_type_mapping import SPGTypeMapping
from kag.builder.component.mapping.relation_mapping import RelationMapping
from kag.builder.component.mapping.spo_mapping import SPOMapping
from kag.builder.component.reader.csv_reader import CSVReader
from kag.builder.component.reader.pdf_reader import PDFReader
from kag.builder.component.reader.json_reader import JSONReader
from kag.builder.component.reader.markdown_reader import MarkDownReader
from kag.builder.component.reader.docx_reader import DocxReader
from kag.builder.component.reader.txt_reader import TXTReader
from kag.builder.component.reader.dataset_reader import (
    HotpotqaCorpusReader,
    TwowikiCorpusReader,
    MusiqueCorpusReader,
)
from kag.builder.component.reader.yuque_reader import YuqueReader
from kag.builder.component.splitter.length_splitter import LengthSplitter
from kag.builder.component.splitter.pattern_splitter import PatternSplitter
from kag.builder.component.splitter.outline_splitter import OutlineSplitter
from kag.builder.component.splitter.semantic_splitter import SemanticSplitter
from kag.builder.component.vectorizer.batch_vectorizer import BatchVectorizer
from kag.builder.component.writer.kg_writer import KGWriter


__all__ = [
    "KAGExtractor",
    "SPGExtractor",
    "KAGPostProcessorAligner",
    "SPGPostProcessorAligner",
    "KGWriter",
    "SPGTypeMapping",
    "RelationMapping",
    "SPOMapping",
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
    "LengthSplitter",
    "PatternSplitter",
    "OutlineSplitter",
    "SemanticSplitter",
    "BatchVectorizer",
    "KGWriter",
]
