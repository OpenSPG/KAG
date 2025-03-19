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

from kag.common.utils import generate_hash_id
from kag.builder.model.chunk import Chunk
from kag.builder.model.sub_graph import SubGraph

logger = logging.getLogger(__name__)


@KAGBuilderChain.register("unstructured_double_reader_builder_chain")
class DefaultUnstructuredDoubleReaderBuilderChain(KAGBuilderChain):
    """
    A class representing a default unstructured builder chain, used to build a knowledge graph from unstructured text data such as txt and pdf files.
    It consists of a reader, splitter, extractor, vectorizer, optional post-processor, and writer components.
    """

    def __init__(
        self,
        reader: ReaderABC,
        reader2: ReaderABC = None,
        splitter: SplitterABC = None,
        extractor: ExtractorABC = None,
        vectorizer: VectorizerABC = None,
        writer: SinkWriterABC = None,
        post_processor: PostProcessorABC = None,
    ):
        """
        Initializes the DefaultUnstructuredBuilderChain instance.

        Args:
            reader (ReaderABC): The reader component to be used.
            splitter (SplitterABC): The splitter component to be used.
            extractor (ExtractorABC): The extractor component to be used.
            vectorizer (VectorizerABC): The vectorizer component to be used.
            writer (SinkWriterABC): The writer component to be used.
            post_processor (PostProcessorABC, optional): The post-processor component to be used. Defaults to None.
        """
        self.reader = reader
        self.reader2 = reader2
        self.splitter = splitter
        self.extractor = extractor
        self.vectorizer = vectorizer
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

        def collect_reader_outputs(data):
            chunks = []
            subgraphs = []

            def collect(data):
                if isinstance(data, Chunk):
                    chunks.append(data)
                elif isinstance(data, SubGraph):
                    subgraphs.append(data)
                elif isinstance(data, (tuple, list)):
                    for item in data:
                        collect(item)
                else:
                    logger.debug(
                        f"expect Chunk and SubGraph nested in tuple and list; found {data.__class__}"
                    )

            collect(data)
            return chunks, subgraphs

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
                self.writer,
            ]:
                if node is None:
                    continue
                flow_data = execute_node(node, flow_data, key=input_key)
            return {input_key: flow_data[0]}

        def write_outline_subgraph(subgraph):
            flow_data = [subgraph]
            for node in [
                self.vectorizer,
                self.writer,
            ]:
                if node is None:
                    continue
                flow_data = execute_node(node, flow_data)

        reader_output = self.reader.invoke(input_data, key=generate_hash_id(input_data))
        if self.reader2:
            reader_output = self.reader2.invoke(
                reader_output, key=generate_hash_id(reader_output)
            )
        chunks, subgraphs = collect_reader_outputs(reader_output)

        if subgraphs:
            if self.splitter is not None:
                logger.debug(
                    "when reader outputs SubGraph, splitter in chain is ignored; you can split chunks in reader"
                )
            for subgraph in subgraphs:
                write_outline_subgraph(subgraph)
            splitter_output = chunks
        else:
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
                result.append(ret)
        return result
