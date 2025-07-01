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

# flake8: noqa
import re
from typing import Type, List, Union


from kag.builder.model.chunk import Chunk
from kag.interface import SplitterABC
from kag.common.utils import generate_hash_id
from knext.common.base.runnable import Input, Output


@SplitterABC.register("pattern")
@SplitterABC.register("pattern_splitter")
class PatternSplitter(SplitterABC):
    """
    A class for splitting text content based on specified patterns and chunking strategies.
    """

    def __init__(self, pattern_dict: dict = None, chunk_cut_num: int = None):
        """
        Initializes the PatternSplitter with the given pattern dictionary and chunk cut number.

        Args:
            pattern_dict (dict, optional): A dictionary containing the pattern and group mappings.
                Defaults to a predefined pattern if not provided.
                Example:
                {
                    "pattern": r"(\d+).([^0-9]+?)？([^0-9第版].*?)(?=\d+\.|$)",
                    "group": {"header": 2, "name": 2, "content": 0}
                }
            chunk_cut_num (int, optional): The number of characters to cut chunks into. Defaults to None.
        """
        super().__init__()
        if pattern_dict is None:
            pattern_dict = {
                "pattern": r"(\d+)\.([^0-9]+?)？([^0-9第版].*?)(?=\d+\.|$)",
                "group": {"header": 2, "name": 2, "content": 0},
            }
        self.pattern = pattern_dict["pattern"]
        self.group = pattern_dict["group"]
        self.chunk_cut_num = chunk_cut_num

    @property
    def input_types(self) -> Type[Input]:
        """The type of input this Runnable object accepts specified as a type annotation."""
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        """The type of output this Runnable object produces specified as a type annotation."""
        return List[Chunk]

    def split_sentence(self, content):
        """
        Splits the given content into sentences based on delimiters.

        Args:
            content (str): The content to be split into sentences.

        Returns:
            List[str]: A list of sentences extracted from the content.
        """
        sentence_delimiters = "。？?！!；;\n"
        output = []
        start = 0
        for idx, char in enumerate(content):
            if char in sentence_delimiters:
                end = idx
                tmp = content[start : end + 1].strip()
                if len(tmp) > 0:
                    output.append(tmp)
                start = idx + 1
        res = content[start:]
        if len(res) > 0:
            output.append(res)
        return output

    def slide_window_chunk(
        self,
        content: Union[str, List[str]],
        chunk_size: int = 2000,
        window_length: int = 300,
        sep: str = "\n",
        prefix: str = "SlideWindow",
    ) -> List[Chunk]:
        """
        Splits the content into chunks using a sliding window approach.

        Args:
            content (Union[str, List[str]]): The content to be chunked.
            chunk_size (int, optional): The maximum size of each chunk. Defaults to 2000.
            window_length (int, optional): The length of the sliding window. Defaults to 300.
            sep (str, optional): The separator to join sentences within a chunk. Defaults to "\n".
            prefix (str, optional): The prefix to use for chunk names. Defaults to "SlideWindow".

        Returns:
            List[Chunk]: A list of Chunk objects representing the chunked content.
        """
        if isinstance(content, str):
            content = self.split_sentence(content)
        splitted = []
        cur = []
        cur_len = 0
        for sentence in content:
            if cur_len + len(sentence) > chunk_size:
                splitted.append(cur)
                tmp = []
                cur_len = 0
                for item in cur[::-1]:
                    if cur_len >= window_length:
                        break
                    tmp.append(item)
                    cur_len += len(item)
                cur = tmp[::-1]

            cur.append(sentence)
            cur_len += len(sentence)
        if len(cur) > 0:
            splitted.append(cur)

        output = []
        for idx, sentences in enumerate(splitted):
            chunk_name = f"{prefix}#{idx}"
            chunk = Chunk(
                id=generate_hash_id(chunk_name),
                name=chunk_name,
                content=sep.join(sentences),
            )
            output.append(chunk)
        return output

    def chunk_split(
        self,
        chunk: Chunk,
    ) -> List[Chunk]:
        """
        Splits the given chunk into smaller chunks based on the pattern and chunk cut number.

        Args:
            chunk (Chunk): The chunk to be split.

        Returns:
            List[Chunk]: A list of smaller Chunk objects.
        """
        text = chunk.content

        pattern = re.compile(self.pattern, re.DOTALL)

        # 查找所有匹配项
        matches = pattern.finditer(text)

        # 遍历所有匹配项
        chunks = []
        for match in matches:
            chunk = Chunk(
                chunk_header=match.group(self.group["header"]),
                name=match.group(self.group["name"]),
                id=generate_hash_id(match.group(self.group["content"])),
                content=match.group(self.group["content"]),
            )
            chunk = [chunk]

            if self.chunk_cut_num:
                chunk = self.slide_window_chunk(
                    content=chunk[0].content,
                    chunk_size=self.chunk_cut_num,
                    window_length=self.chunk_cut_num / 4,
                    sep="\n",
                    prefix=chunk[0].name,
                )

            chunks.extend(chunk)

        return chunks

    def _invoke(self, input: Chunk, **kwargs) -> List[Output]:
        """
        Invokes the chunk splitting process on the given input.

        Args:
            input (Chunk): The input chunk to be processed.
            **kwargs: Additional keyword arguments, currently unused but kept for potential future expansion.

        Returns:
            List[Output]: A list of output chunks.
        """
        chunks = self.chunk_split(input)
        return chunks
