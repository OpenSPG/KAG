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

from kag.builder.component.external_graph.external_graph import (
    DefaultExternalGraphLoader,
)
from kag.builder.component.extractor.kag_extractor import KAGExtractor
from kag.builder.component.extractor.spg_extractor import SPGExtractor
from kag.builder.component.aligner.kag_aligner import KAGAligner
from kag.builder.component.aligner.spg_aligner import SPGAligner
from kag.builder.component.postprocessor.kag_postprocessor import KAGPostProcessor

from kag.builder.component.mapping.spg_type_mapping import SPGTypeMapping
from kag.builder.component.mapping.relation_mapping import RelationMapping
from kag.builder.component.mapping.spo_mapping import SPOMapping
from kag.builder.component.reader.csv_reader import CSVReader
from kag.builder.component.reader.json_reader import JSONReader
from kag.builder.component.reader.yuque_reader import YuqueReader
from kag.builder.component.reader.dataset_reader import (
    MusiqueCorpusReader,
    HotpotqaCorpusReader,
)
from kag.builder.component.reader.file_reader import FileReader
from kag.builder.component.reader.directory_reader import DirectoryReader


from kag.builder.component.record_parser.pdf_parser import PDFParser
from kag.builder.component.record_parser.markdown_parser import MarkDownParser
from kag.builder.component.record_parser.docx_parser import DocxParser
from kag.builder.component.record_parser.txt_parser import TXTParser
from kag.builder.component.record_parser.mix_parser import MixParser

from kag.builder.component.record_parser.dict_parser import DictParser


from kag.builder.component.splitter.length_splitter import LengthSplitter
from kag.builder.component.splitter.pattern_splitter import PatternSplitter
from kag.builder.component.splitter.outline_splitter import OutlineSplitter
from kag.builder.component.splitter.semantic_splitter import SemanticSplitter
from kag.builder.component.vectorizer.batch_vectorizer import BatchVectorizer
from kag.builder.component.writer.kg_writer import KGWriter


__all__ = [
    "DefaultExternalGraphLoader",
    "KAGExtractor",
    "SPGExtractor",
    "KAGAligner",
    "SPGAligner",
    "KAGPostProcessor",
    "KGWriter",
    "SPGTypeMapping",
    "RelationMapping",
    "SPOMapping",
    "TXTParser",
    "PDFParser",
    "MarkDownParser",
    "DocxParser",
    "MixParser",
    "DictParser",
    "JSONReader",
    "HotpotqaCorpusReader",
    "MusiqueCorpusReader",
    "FileReader",
    "DirectoryReader",
    "YuqueReader",
    "CSVReader",
    "LengthSplitter",
    "PatternSplitter",
    "OutlineSplitter",
    "SemanticSplitter",
    "BatchVectorizer",
    "KGWriter",
]
