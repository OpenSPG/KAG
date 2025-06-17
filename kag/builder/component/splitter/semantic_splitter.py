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
import re
from typing import List, Type

from kag.interface import SplitterABC
from kag.builder.prompt.semantic_seg_prompt import SemanticSegPrompt
from kag.builder.model.chunk import Chunk
from kag.interface import LLMClient
from kag.common.utils import generate_hash_id
from knext.common.base.runnable import Input, Output

logger = logging.getLogger(__name__)


@SplitterABC.register("semantic")
@SplitterABC.register("semantic_splitter")
class SemanticSplitter(SplitterABC):
    """
    A class for semantically splitting text into smaller chunks based on the content's structure and meaning.
    Inherits from the SplitterABC class.

    """

    def __init__(
        self,
        llm: LLMClient,
        kept_char_pattern: str = None,
        split_length: int = 1000,
        **kwargs,
    ):
        """
        Initializes the SemanticSplitter with the given LLMClient, kept character pattern, and split length.

        Args:
            llm (LLMClient): Instance of LLMClient initialized with `model` config.
            kept_char_pattern (str, optional): Regex pattern to match Chinese/ASCII characters.
                Defaults to a predefined pattern if not provided.
            split_length (int, optional): The maximum length of each chunk after splitting. Defaults to 1000.
            **kwargs: Additional keyword arguments to be passed to the superclass.
        """
        super().__init__(**kwargs)
        # Chinese/ASCII characters
        if kept_char_pattern is None:
            self.kept_char_pattern = re.compile(
                r"[^\u4e00-\u9fa5\u3000-\u303F\uFF01-\uFF0F\uFF1A-\uFF20\uFF3B-\uFF40\uFF5B-\uFF65\x00-\x7F]+"
            )
        else:
            self.kept_char_pattern = re.compile(kept_char_pattern)
        self.split_length = split_length
        self.llm = llm
        self.semantic_seg_op = SemanticSegPrompt(self.kag_project_config.language)

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return Chunk

    @staticmethod
    def parse_llm_output(content: str, llm_output: list):
        """
        Parses the output from the LLM to generate segmented information.

        Args:
            content (str): The original content being split.
            llm_output (list): Output from the LLM indicating segment locations and abstracts.

        Returns:
            list: A list of dictionaries containing segment names, contents, and lengths.
        """
        seg_info = llm_output

        seg_info.sort()
        locs = [x[0] for x in seg_info]
        abstracts = [x[1] for x in seg_info]
        locs.append(len(content))
        splitted = []
        for idx in range(len(abstracts)):
            start = locs[idx]
            end = locs[idx + 1]
            splitted.append(
                {
                    "name": abstracts[idx],
                    "content": content[start:end],
                    "length": end - start,
                }
            )

        return splitted

    def semantic_chunk(
        self,
        org_chunk: Chunk,
        chunk_size: int = 1000,
    ) -> List[Chunk]:
        """
        Splits the given content into semantic chunks using an LLM.

        Args:
            org_chunk (Chunk): The original chunk to be split.
            chunk_size (int, optional): Maximum size of each chunk. Defaults to 1000.

        Returns:
            List[Chunk]: A list of Chunk objects representing the split content.
        """
        result = self.llm.invoke({"input": org_chunk.content}, self.semantic_seg_op)
        splitted = self.parse_llm_output(org_chunk.content, result)
        if len(splitted) == 0:
            return [org_chunk]
        logger.debug(f"splitted = {splitted}")
        chunks = []
        for idx, item in enumerate(splitted):
            split_name = item["name"]
            if len(item["content"]) < chunk_size:
                chunk = Chunk(
                    id=f"{org_chunk.id}#{chunk_size}#{idx}#SEM",
                    name=f"{org_chunk.name}#{split_name}",
                    content=item["content"],
                    abstract=item["name"],
                    **org_chunk.kwargs,
                )
                chunks.append(chunk)
            else:
                print("chunk over size")
                innerChunk = Chunk(
                    id=generate_hash_id(item["content"]),
                    name=f"{org_chunk.name}#{split_name}",
                    content=item["content"],
                )
                chunks.extend(self.semantic_chunk(innerChunk, chunk_size))
        return chunks

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the splitting process on the provided input.

        Args:
            input (Input): The input to be processed.
            **kwargs: Additional keyword arguments, currently unused but kept for potential future expansion.

        Returns:
            List[Output]: A list of outputs generated from the input.
        """
        chunks = self.semantic_chunk(input, self.split_length)
        return chunks
