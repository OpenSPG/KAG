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
from concurrent.futures import ThreadPoolExecutor, as_completed
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

from kag.common.utils import generate_hash_id

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

    def get_component_with_ckpts(self):
        return [
            self.mapping,
            self.vectorizer,
            self.writer,
        ]

    def close_checkpointers(self):
        for node in self.get_component_with_ckpts():
            if node and hasattr(node, "checkpointer"):
                node.checkpointer.close()


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
        pass

    def invoke(self, input_data, max_workers=10, **kwargs):
        """
        Invokes the builder chain to process the input file.

        Args:
            file_path: The path to the input file to be processed.
            max_workers (int, optional): The maximum number of threads to use. Defaults to 10.
            **kwargs: Additional keyword arguments.

        Returns:
            List: The final output from the builder chain.
        """

        def execute_node(node, node_input, **kwargs):
            if not isinstance(node_input, list):
                node_input = [node_input]
            node_output = []
            for item in node_input:
                node_output.extend(node.invoke(item, **kwargs))
            return node_output

        def run_extract(chunk):
            flow_data = [chunk]
            input_key = chunk.hash_key
            for node in [
                self.extractor,
                self.vectorizer,
                self.post_processor,
                self.writer,
            ]:
                if node is None:
                    continue
                flow_data = execute_node(node, flow_data, key=input_key)
            return flow_data

        parser_output = self.parser.invoke(input_data, key=generate_hash_id(input_data))
        splitter_output = []
        for chunk in parser_output:
            splitter_output.extend(
                self.splitter.invoke(parser_output, key=chunk.hash_key)
            )

        result = []
        with ThreadPoolExecutor(max_workers) as executor:
            futures = [executor.submit(run_extract, chunk) for chunk in splitter_output]

            from tqdm import tqdm

            for inner_future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Chunk Extraction",
                position=1,
                leave=False,
            ):
                ret = inner_future.result()
                result.extend(ret)
        return result

    def get_component_with_ckpts(self):
        return [
            self.parser,
            self.splitter,
            self.extractor,
            self.vectorizer,
            self.post_processor,
            self.writer,
        ]

    def close_checkpointers(self):
        for node in self.get_component_with_ckpts():
            if node and hasattr(node, "checkpointer"):
                node.checkpointer.close()
