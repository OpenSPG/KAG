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

from kag.builder.component import KGWriter
from kag.builder.component.table.table_vectorizer import TableBatchVectorizer
from kag.builder.component.table.table_classify import TableClassify
from kag.builder.component.table.table_extractor import TableExtractor
from kag.builder.default_chain import get_reader
from knext.common.base.chain import Chain
from knext.builder.builder_chain_abc import BuilderChainABC


logger = logging.getLogger(__name__)


class DefaultUnstructuredTableBuilderChain(BuilderChainABC):
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
        source = get_reader(file_path)()
        table_classify = TableClassify()
        extractor = TableExtractor()
        vectorizer = TableBatchVectorizer()
        sink = KGWriter()

        chain = source >> table_classify >> extractor >> vectorizer >> sink
        return chain

    def invoke(
        self,
        file_path: str,
        max_workers=10,
        **kwargs,
    ):
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
        return super().invoke(
            file_path=file_path,
            max_workers=max_workers,
            **kwargs,
        )
