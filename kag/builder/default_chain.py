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

from kag.builder.component import SPGTypeMapping, KGWriter
from kag.builder.component.extractor import KAGExtractor
from kag.builder.component.splitter import LengthSplitter
from kag.builder.component.vectorizer.batch_vectorizer import BatchVectorizer
from knext.common.base.chain import Chain
from knext.builder.builder_chain_abc import BuilderChainABC

logger = logging.getLogger(__name__)


def get_reader(file_path: str):
    file = os.path.basename(file_path)
    suffix = file.split(".")[-1]
    assert suffix.lower() in READER_MAPPING, f"{suffix} is not supported. Supported suffixes are: {list(READER_MAPPING.keys())}"
    reader_path = READER_MAPPING.get(suffix.lower())
    mod_path, class_name = reader_path.rsplit('.', 1)
    module = importlib.import_module(mod_path)
    reader_class = getattr(module, class_name)

    return reader_class


READER_MAPPING = {
    "csv": "kag.builder.component.reader.csv_reader.CSVReader",
    "json": "kag.builder.component.reader.json_reader.JSONReader",
    "txt": "kag.builder.component.reader.txt_reader.TXTReader",
    "pdf": "kag.builder.component.reader.pdf_reader.PDFReader",
    "docx": "kag.builder.component.reader.docx_reader.DocxReader",
    "md": "kag.builder.component.reader.markdown_reader.MarkdownReader",
}


class DefaultStructuredBuilderChain(BuilderChainABC):
    """
    A class representing a default SPG builder chain, used to import structured data based on schema definitions

    Steps:
        0. Initializing by a give SpgType name, which indicates the target of import.
        1. SourceReader: Reading structured dicts from a given file.
        2. SPGTypeMapping: Mapping source fields to the properties of target type, and assemble a sub graph.
        By default, the same name mapping is used, which means importing the source field into a property with the same name.
        3. KGWriter: Writing sub graph into KG storage.

    Attributes:
        spg_type_name (str): The name of the SPG type.
    """

    def __init__(self, spg_type_name: str, **kwargs):
        super().__init__(**kwargs)
        self.spg_type_name = spg_type_name

    def build(self, **kwargs):
        """
        Builds the processing chain for the SPG.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            chain: The constructed processing chain.
        """
        file_path = kwargs.get("file_path")
        source = get_reader(file_path)(output_type="Dict")
        mapping = SPGTypeMapping(spg_type_name=self.spg_type_name)
        sink = KGWriter()

        chain = source >> mapping >> sink
        return chain

    def invoke(self, file_path, max_workers=10, **kwargs):
        logger.info(f"begin processing file_path:{file_path}")
        """
        Invokes the processing chain with the given file path and optional parameters.

        Args:
            file_path (str): The path to the input file.
            max_workers (int, optional): The maximum number of workers. Defaults to 10.
            **kwargs: Additional keyword arguments.

        Returns:
            The result of invoking the processing chain.
        """
        return super().invoke(file_path=file_path, max_workers=max_workers, **kwargs)


class DefaultUnstructuredBuilderChain(BuilderChainABC):
    """
    A class representing a default KAG builder chain, used to extract graph from documents and import unstructured data.

    Steps:
        0. Initializing.
        1. SourceReader: Reading chunks from a given file.
        2. LengthSplitter: Splitting chunk to smaller chunks. The chunk size can be adjusted through parameters.
        3. KAGExtractor: Extracting entities and relations from chunks, and assembling a sub graph.
            By default,the extraction process includes NER and SPO Extraction.
        4. KGWriter: Writing sub graph into KG storage.

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self, **kwargs) -> Chain:
        """
        Builds the processing chain for the KAG.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            chain: The constructed processing chain.
        """
        file_path = kwargs.get("file_path")
        split_length = kwargs.get("split_length")
        window_length = kwargs.get("window_length")
        source = get_reader(file_path)()
        splitter = LengthSplitter(split_length, window_length)
        extractor = KAGExtractor()
        vectorizer = BatchVectorizer()
        sink = KGWriter()

        chain = source >> splitter >> extractor >> vectorizer >> sink
        return chain

    def invoke(self, file_path: str, split_length: int = 500, window_length: int = 100, max_workers=10, **kwargs):
        logger.info(f"begin processing file_path:{file_path}")
        """
        Invokes the processing chain with the given file path and optional parameters.

        Args:
            file_path (str): The path to the input file.
            split_length (int, optional): The length at which the file should be split. Defaults to 500.
            window_length (int, optional): The length of the processing window. Defaults to 100.
            max_workers (int, optional): The maximum number of worker threads. Defaults to 10.

            **kwargs: Additional keyword arguments.

        Returns:
            The result of invoking the processing chain.
        """
        return super().invoke(file_path=file_path, max_workers=max_workers, split_length=window_length, window_length=window_length, **kwargs)
