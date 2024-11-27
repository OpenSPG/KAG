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


from kag.interface import (
    RecordParserABC,
    MappingABC,
    ExtractorABC,
    SplitterABC,
    VectorizerABC,
    PostProcessorABC,
    SinkWriterABC,
    KAGBuilderChain,
)

logger = logging.getLogger(__name__)


@KAGBuilderChain.register("structured")
class DefaultStructuredBuilderChain(KAGBuilderChain):
    """
    A class representing a default SPG builder chain, used to import structured data based on schema definitions.
    It consists of a mapping component, a writer component, and an optional vectorizer component.
    """

    def __init__(
        self,
        mapping: MappingABC,
        writer: SinkWriterABC,
        vectorizer: VectorizerABC = None,
    ):
        """
        Initializes the DefaultStructuredBuilderChain instance.

        Args:
            mapping (MappingABC): The mapping component to be used.
            writer (SinkWriterABC): The writer component to be used.
            vectorizer (VectorizerABC, optional): The vectorizer component to be used. Defaults to None.
        """
        self.mapping = mapping
        self.writer = writer
        self.vectorizer = vectorizer

    def build(self, **kwargs):
        """
        Construct the builder chain by connecting the mapping, vectorizer (if available), and writer components.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            KAGBuilderChain: The constructed builder chain.
        """
        if self.vectorizer:
            chain = self.mapping >> self.vectorizer >> self.writer
        else:
            chain = self.mapping >> self.writer

        return chain


@KAGBuilderChain.register("unstructured")
class DefaultUnstructuredBuilderChain(KAGBuilderChain):
    """
    A class representing a default unstructured builder chain, used to build a knowledge graph from unstructured text data such as txt and pdf files.
    It consists of a parser, splitter, extractor, vectorizer, optional post-processor, and writer components.
    """

    def __init__(
        self,
        parser: RecordParserABC,
        splitter: SplitterABC,
        extractor: ExtractorABC,
        vectorizer: VectorizerABC,
        writer: SinkWriterABC,
        post_processor: PostProcessorABC = None,
    ):
        """
        Initializes the DefaultUnstructuredBuilderChain instance.

        Args:
            parser (RecordParserABC): The parser component to be used.
            splitter (SplitterABC): The splitter component to be used.
            extractor (ExtractorABC): The extractor component to be used.
            vectorizer (VectorizerABC): The vectorizer component to be used.
            writer (SinkWriterABC): The writer component to be used.
            post_processor (PostProcessorABC, optional): The post-processor component to be used. Defaults to None.
        """
        self.parser = parser
        self.splitter = splitter
        self.extractor = extractor
        self.vectorizer = vectorizer
        self.post_processor = post_processor
        self.writer = writer

    def build(self, **kwargs):
        """
        Builds the builder chain by connecting the parser, splitter, extractor, vectorizer, post-processor (if available), and writer components.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            KAGBuilderChain: The constructed builder chain.
        """
        if self.post_processor:
            return (
                self.parser
                >> self.splitter
                >> self.extractor
                >> self.vectorizer
                >> self.post_processor
                >> self.writer
            )
        return (
            self.parser
            >> self.splitter
            >> self.extractor
            >> self.vectorizer
            >> self.writer
        )
