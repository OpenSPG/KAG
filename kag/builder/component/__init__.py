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
from kag.builder.component.extractor.knowledge_unit_extractor import (
    KnowledgeUnitSchemaFreeExtractor,
)
from kag.builder.component.extractor.naive_rag_extractor import NaiveRagExtractor
from kag.builder.component.extractor.schema_free_extractor import SchemaFreeExtractor
from kag.builder.component.extractor.schema_constraint_extractor import (
    SchemaConstraintExtractor,
)
from kag.builder.component.extractor.table_extractor import TableExtractor
from kag.builder.component.extractor.outline_extractor import OutlineExtractor
from kag.builder.component.extractor.summary_extractor import SummaryExtractor
from kag.builder.component.extractor.chunk_extractor import ChunkExtractor
from kag.builder.component.extractor.atomic_query_extractor import AtomicQueryExtractor

from kag.builder.component.aligner.kag_aligner import KAGAligner
from kag.builder.component.aligner.spg_aligner import SPGAligner
from kag.builder.component.postprocessor.kag_postprocessor import KAGPostProcessor

from kag.builder.component.mapping.spg_type_mapping import SPGTypeMapping
from kag.builder.component.mapping.relation_mapping import RelationMapping
from kag.builder.component.mapping.spo_mapping import SPOMapping
from kag.builder.component.scanner.csv_scanner import CSVScanner, CSVStructuredScanner
from kag.builder.component.scanner.json_scanner import JSONScanner
from kag.builder.component.scanner.yuque_scanner import YuqueScanner
from kag.builder.component.scanner.dataset_scanner import (
    MusiqueCorpusScanner,
    HotpotqaCorpusScanner,
)
from kag.builder.component.scanner.file_scanner import FileScanner
from kag.builder.component.scanner.directory_scanner import DirectoryScanner
from kag.builder.component.scanner.odps_scanner import ODPSScanner
from kag.builder.component.scanner.sls_scanner import SLSScanner, SLSConsumerScanner


from kag.builder.component.reader.pdf_reader import PDFReader
from kag.builder.component.reader.markdown_reader import MarkDownReader
from kag.builder.component.reader.docx_reader import DocxReader
from kag.builder.component.reader.txt_reader import TXTReader
from kag.builder.component.reader.mix_reader import MixReader
from kag.builder.component.reader.mp_reader import MPReaderWrapper

from kag.builder.component.reader.dict_reader import DictReader


from kag.builder.component.splitter.length_splitter import LengthSplitter
from kag.builder.component.splitter.pattern_splitter import PatternSplitter
from kag.builder.component.splitter.outline_splitter import OutlineSplitter
from kag.builder.component.splitter.semantic_splitter import SemanticSplitter
from kag.builder.component.vectorizer.batch_vectorizer import BatchVectorizer
from kag.builder.component.writer.kg_writer import KGWriter
from kag.builder.component.writer.memory_graph_writer import MemoryGraphWriter


__all__ = [
    "DefaultExternalGraphLoader",
    "SchemaFreeExtractor",
    "SchemaConstraintExtractor",
    "KAGAligner",
    "SPGAligner",
    "KAGPostProcessor",
    "KGWriter",
    "SPGTypeMapping",
    "RelationMapping",
    "SPOMapping",
    "TXTReader",
    "PDFReader",
    "MarkDownReader",
    "DocxReader",
    "MixReader",
    "MPReaderWrapper",
    "DictReader",
    "JSONScanner",
    "HotpotqaCorpusScanner",
    "MusiqueCorpusScanner",
    "FileScanner",
    "DirectoryScanner",
    "YuqueScanner",
    "CSVScanner",
    "CSVStructuredScanner",
    "ODPSScanner",
    "LengthSplitter",
    "PatternSplitter",
    "OutlineSplitter",
    "SemanticSplitter",
    "BatchVectorizer",
    "KGWriter",
    "SLSScanner",
    "SLSConsumerScanner",
    "NaiveRagExtractor",
    "TableExtractor",
    "AtomicQueryExtractor",
    "KnowledgeUnitSchemaFreeExtractor",
    "ChunkExtractor",
    "OutlineExtractor",
    "SummaryExtractor",
    "MemoryGraphWriter",
]
