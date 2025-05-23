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
from typing import List, Union

from kag.common.utils import generate_hash_id
from kag.interface import (
    ReaderABC,
    MappingABC,
    ExtractorABC,
    SplitterABC,
    VectorizerABC,
    PostProcessorABC,
    SinkWriterABC,
    KAGBuilderChain,
    ExternalGraphLoaderABC,
)

logger = logging.getLogger(__name__)


@KAGBuilderChain.register("structured")
@KAGBuilderChain.register("structured_builder_chain")
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
@KAGBuilderChain.register("unstructured_builder_chain")
class DefaultUnstructuredBuilderChain(KAGBuilderChain):
    """
    A class representing a default unstructured builder chain, used to build a knowledge graph from unstructured text data such as txt and pdf files.
    It consists of a reader, splitter, extractor, vectorizer, optional post-processor, and writer components.
    """

    def __init__(
        self,
        reader: ReaderABC,
        splitter: SplitterABC = None,
        extractor: Union[ExtractorABC, List[ExtractorABC]] = None,
        vectorizer: VectorizerABC = None,
        writer: SinkWriterABC = None,
        post_processor: PostProcessorABC = None,
    ):
        """
        Initializes the DefaultUnstructuredBuilderChain instance.

        Args:
            reader (ReaderABC): The reader component to be used.
            splitter (SplitterABC): The splitter component to be used.
            extractor (Union[ExtractorABC, List[ExtractorABC]]): The extractor component to be used.
            vectorizer (VectorizerABC): The vectorizer component to be used.
            writer (SinkWriterABC): The writer component to be used.
            post_processor (PostProcessorABC, optional): The post-processor component to be used. Defaults to None.
        """
        self.reader = reader
        self.splitter = splitter
        self.extractor = extractor
        self.vectorizer = vectorizer
        self.post_processor = post_processor
        self.writer = writer

    def build(self, **kwargs):
        chain = self.reader >> self.splitter
        if self.extractor:
            chain = chain >> self.extractor
        if self.vectorizer:
            chain = chain >> self.vectorizer
        if self.post_processor:
            chain = chain >> self.post_processor
        if self.writer:
            chain = chain >> self.writer
        return chain

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
                output = node.invoke(item, **kwargs)
                node_output.extend(output)
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

        reader_output = self.reader.invoke(input_data, key=generate_hash_id(input_data))

        splitter_output = []
        for chunk in reader_output:
            splitter_output.extend(self.splitter.invoke(chunk, key=chunk.hash_key))

        processed_chunk_keys = kwargs.get("processed_chunk_keys", set())
        filtered_chunks = []
        processed = 0
        for chunk in splitter_output:
            if chunk.hash_key not in processed_chunk_keys:
                filtered_chunks.append(chunk)
            else:
                processed += 1
        logger.debug(
            f"Total chunks: {len(splitter_output)}. Checkpointed: {processed}, Pending: {len(filtered_chunks)}."
        )
        result = []
        with ThreadPoolExecutor(max_workers) as executor:
            futures = [executor.submit(run_extract, chunk) for chunk in filtered_chunks]

            from tqdm import tqdm

            for inner_future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="KAG Extraction From Chunk",
                position=1,
                leave=False,
            ):
                ret = inner_future.result()
                result.extend(ret)
        return result


@KAGBuilderChain.register("domain_kg_inject_chain")
class DomainKnowledgeInjectChain(KAGBuilderChain):
    def __init__(
        self,
        external_graph: ExternalGraphLoaderABC,
        writer: SinkWriterABC,
        vectorizer: VectorizerABC = None,
    ):
        """
        Initializes the DefaultStructuredBuilderChain instance.

        Args:
            external_graph (ExternalGraphLoaderABC): The ExternalGraphLoader component to be used.
            writer (SinkWriterABC): The writer component to be used.
            vectorizer (VectorizerABC, optional): The vectorizer component to be used. Defaults to None.
        """
        self.external_graph = external_graph
        self.writer = writer
        self.vectorizer = vectorizer

    def build(self, **kwargs):
        """
        Construct the builder chain by connecting the external_graph, vectorizer (if available), and writer components.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            KAGBuilderChain: The constructed builder chain.
        """
        if self.vectorizer:
            chain = self.external_graph >> self.vectorizer >> self.writer
        else:
            chain = self.external_graph >> self.writer

        return chain
