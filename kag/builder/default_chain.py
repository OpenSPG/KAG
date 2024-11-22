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

    def __init__(
        self,
        mapping: MappingABC,
        writer: SinkWriterABC,
        vectorizer: VectorizerABC = None,
    ):
        self.mapping = mapping
        self.writer = writer
        self.vectorizer = vectorizer
        # self.spg_type_name = spg_type_name
        # self.parser = RecordParserABC.from_config(
        #     {
        #         "type": "dict",
        #         "id_col": id_col,
        #         "name_col": name_col,
        #         "content_col": content_col,
        #     }
        # )
        # self.mapping = MappingABC.from_config(
        #     {"type": "spg", "spg_type_name": self.spg_type_name}
        # )
        # self.writer = SinkWriterABC.from_config({"type": "kg"})

    def build(self, **kwargs):
        """
        Builds the processing chain for the SPG.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            chain: The constructed processing chain.
        """
        # file_path = kwargs.get("file_path")
        # # source = get_reader(file_path)(output_type="Dict")
        # suffix = os.path.basename(file_path).split(".")[-1]
        # source_config = {"type": suffix}
        # if suffix in ["json", "csv"]:
        #     source_config["output_type"] = "Dict"
        # source = SourceReaderABC.from_config(source_config)

        # mapping = SPGTypeMapping(spg_type_name=self.spg_type_name)
        # sink = KGWriter()

        # chain = source >> mapping >> sink
        if self.vectorizer:
            chain = self.mapping >> self.vectorizer >> self.writer
        else:
            chain = self.mapping >> self.writer

        return chain

    # def invoke(self, file_path, max_workers=10, **kwargs):
    #     logger.info(f"begin processing file_path:{file_path}")
    #     """
    #     Invokes the processing chain with the given file path and optional parameters.

    #     Args:
    #         file_path (str): The path to the input file.
    #         max_workers (int, optional): The maximum number of workers. Defaults to 10.
    #         **kwargs: Additional keyword arguments.

    #     Returns:
    #         The result of invoking the processing chain.
    #     """
    #     return super().invoke(file_path=file_path, max_workers=max_workers, **kwargs)


# @KAGBuilderChain.register("structured")
# class DefaultStructuredBuilderChain(KAGBuilderChain):

#     """
#     A class representing a default SPG builder chain, used to import structured data based on schema definitions

#     Steps:
#         0. Initializing by a give SpgType name, which indicates the target of import.
#         1. SourceReader: Reading structured dicts from a given file.
#         2. SPGTypeMapping: Mapping source fields to the properties of target type, and assemble a sub graph.
#         By default, the same name mapping is used, which means importing the source field into a property with the same name.
#         3. KGWriter: Writing sub graph into KG storage.

#     Attributes:
#         spg_type_name (str): The name of the SPG type.
#     """

#     def __init__(self, spg_type_name: str, **kwargs):
#         super().__init__(**kwargs)
#         self.spg_type_name = spg_type_name

#     def build(self, **kwargs):
#         """
#         Builds the processing chain for the SPG.

#         Args:
#             **kwargs: Additional keyword arguments.

#         Returns:
#             chain: The constructed processing chain.
#         """
#         file_path = kwargs.get("file_path")
#         # source = get_reader(file_path)(output_type="Dict")
#         suffix = os.path.basename(file_path).split(".")[-1]
#         source_config = {"type": suffix}
#         if suffix in ["json", "csv"]:
#             source_config["output_type"] = "Dict"
#         source = SourceReaderABC.from_config(source_config)

#         mapping = SPGTypeMapping(spg_type_name=self.spg_type_name)
#         sink = KGWriter()

#         chain = source >> mapping >> sink
#         return chain

#     def invoke(self, file_path, max_workers=10, **kwargs):
#         logger.info(f"begin processing file_path:{file_path}")
#         """
#         Invokes the processing chain with the given file path and optional parameters.

#         Args:
#             file_path (str): The path to the input file.
#             max_workers (int, optional): The maximum number of workers. Defaults to 10.
#             **kwargs: Additional keyword arguments.

#         Returns:
#             The result of invoking the processing chain.
#         """
#         return super().invoke(file_path=file_path, max_workers=max_workers, **kwargs)


@KAGBuilderChain.register("unstructured")
class DefaultUnstructuredBuilderChain(KAGBuilderChain):
    def __init__(
        self,
        parser: RecordParserABC,
        splitter: SplitterABC,
        extractor: ExtractorABC,
        vectorizer: VectorizerABC,
        writer: SinkWriterABC,
        post_processor: PostProcessorABC = None,
    ):
        self.parser = parser
        self.splitter = splitter
        self.extractor = extractor
        self.vectorizer = vectorizer
        self.post_processor = post_processor
        self.writer = writer

    def build(self, **kwargs):
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
