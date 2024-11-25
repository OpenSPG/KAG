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
import os
import re
from typing import List, Type

from kag.builder.component.base import Splitter
from kag.builder.prompt.semantic_seg_prompt import SemanticSegPrompt
from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.common.base.runnable import Input, Output
from kag.common.llm.client.llm_client import LLMClient

logger = logging.getLogger(__name__)


class SemanticSplitter(Splitter):
    """
    A class for semantically splitting text into smaller chunks based on the content's structure and meaning.
    Inherits from the Splitter class.

    Attributes:
        kept_char_pattern (re.Pattern): Regex pattern to match Chinese/ASCII characters.
        split_length (int): The maximum length of each chunk after splitting.
        llm_client (LLMClient): Instance of LLMClient initialized with `model` config.
        semantic_seg_op (SemanticSegPrompt): Instance of SemanticSegPrompt for semantic segmentation.
    """

    def __init__(self, split_length: int = 1000):
        super().__init__()
        # Chinese/ASCII characters
        self.kept_char_pattern = re.compile(
            r"[^\u4e00-\u9fa5\u3000-\u303F\uFF01-\uFF0F\uFF1A-\uFF20\uFF3B-\uFF40\uFF5B-\uFF65\x00-\x7F]+"
        )
        self.split_length = int(split_length)
        llm_config = eval(os.getenv("KAG_LLM", "{}"))
        self.llm_client = LLMClient.from_config(llm_config)
        language = os.getenv("KAG_PROMPT_LANGUAGE", "zh")
        self.semantic_seg_op = SemanticSegPrompt(language)

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
            content (str): The content to be split.
            chunk_size (int, optional): Maximum size of each chunk. Defaults to 1000.
            prefix (str, optional): Prefix for the chunk name. Defaults to "SemanticChunk".

        Returns:
            List[Chunk]: A list of Chunk objects representing the split content.
        """
        result = self.llm_client.invoke({"input": org_chunk.content}, self.semantic_seg_op)
        splitted = self.parse_llm_output(org_chunk.content, result)
        logger.debug(f"splitted = {splitted}")
        chunks = []
        for idx, item in enumerate(splitted):
            if len(item["content"]) < chunk_size:
                chunk = Chunk(
                    id=f"{org_chunk.id}#{chunk_size}#{idx}#SEM",
                    name=f"{org_chunk.name}#{idx}",
                    content=item["content"],
                    abstract=item["name"],
                    **org_chunk.kwargs
                )
                chunks.append(chunk)
            else:
                print("chunk over size")
                chunks.extend(
                    self.semantic_chunk(
                        item["content"], chunk_size, f"{prefix}#SubLevel"
                    )
                )
        return chunks

    def chunk_split(self, chunk: Chunk) -> List[Chunk]:
        """
        Splits a given chunk into smaller chunks based on its content structure.

        Args:
            chunk (Chunk): The chunk to be split further.

        Returns:
            List[Chunk]: A list of Chunk objects representing the split content.
        """
        chapters = []
        max_len = 0
        paragraphs = []
        content = chunk.content
        basename = chunk.name
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("$$"):
                line = line[2:]
                chapters.append(len(paragraphs))
            paragraphs.append(line)
            max_len = max(max_len, len(line))
        chapters.append(len(paragraphs))
        book = {}
        if len(chapters) > 1:
            for i in range(len(chapters) - 1):
                start = chapters[i]
                end = chapters[i + 1]
                chapter_name = paragraphs[start]
                book[chapter_name] = paragraphs[start + 1 : end]
        else:
            book[basename] = paragraphs

        cutted = []
        for k, v in book.items():
            prefix = f"{basename}#{k}" if k != basename else basename
            cutted.extend(
                self.semantic_chunk(
                    "".join(v), chunk_size=self.split_length, prefix=prefix
                )
            )
        return cutted

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the splitting process on the provided input.

        Args:
            input (Input): The input to be processed.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of outputs generated from the input.
        """
        chunks = self.chunk_split(input)
        return chunks
