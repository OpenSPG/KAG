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

from typing import Type, List, Union

from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from knext.common.base.runnable import Input, Output
from kag.builder.component.splitter.base_table_splitter import BaseTableSplitter


class LengthSplitter(BaseTableSplitter):
    """
    A class for splitting text based on length, inheriting from Splitter.

    Attributes:
        split_length (int): The maximum length of each split chunk.
        window_length (int): The length of the overlap between chunks.
    """

    def __init__(self, split_length: int = 500, window_length: int = 100, **kwargs):
        super().__init__(**kwargs)
        self.split_length = int(split_length)
        self.window_length = int(window_length)

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return Chunk

    def split_sentence(self, content):
        """
        Splits the given content into sentences based on delimiters.

        Args:
            content (str): The content to be split.

        Returns:
            list: A list of sentences.
        """
        sentence_delimiters = ".。？?！!"
        output = []
        start = 0
        for idx, char in enumerate(content):
            if char in sentence_delimiters:
                end = idx
                tmp = content[start: end + 1].strip()
                if len(tmp) > 0:
                    output.append(tmp)
                start = idx + 1
        res = content[start:]
        if len(res) > 0:
            output.append(res)
        return output

    def slide_window_chunk(
            self,
            org_chunk: Chunk,
            chunk_size: int = 2000,
            window_length: int = 300,
            sep: str = "\n",
    ) -> List[Chunk]:
        """
        Splits the content into chunks using a sliding window approach.

        Args:
            org_chunk (Chunk): The original chunk to be split.
            chunk_size (int, optional): The maximum size of each chunk. Defaults to 2000.
            window_length (int, optional): The length of the overlap between chunks. Defaults to 300.
            sep (str, optional): The separator used to join sentences. Defaults to "\n".

        Returns:
            List[Chunk]: A list of Chunk objects.
        """
        if org_chunk.type == ChunkTypeEnum.Table:
            table_chunks = self.split_table(org_chunk=org_chunk, chunk_size=chunk_size, sep=sep)
            if table_chunks is not None:
                return table_chunks
        content = self.split_sentence(org_chunk.content)
        splitted = []
        cur = []
        cur_len = 0
        for sentence in content:
            if cur_len + len(sentence) > chunk_size:
                if cur:
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
            chunk = Chunk(
                id=f"{org_chunk.id}#{chunk_size}#{window_length}#{idx}#LEN",
                name=f"{org_chunk.name}",
                content=sep.join(sentences),
                type=org_chunk.type,
                **org_chunk.kwargs
            )
            output.append(chunk)
        return output

    def invoke(self, input: Chunk, **kwargs) -> List[Output]:
        """
        Invokes the splitter on the given input chunk.

        Args:
            input (Chunk): The input chunk to be split.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of split chunks.
        """
        cutted = []
        if isinstance(input,list):
            for item in input:
                cutted.extend(
                    self.slide_window_chunk(
                        item, self.split_length, self.window_length
                    )
                )
        else:
            cutted.extend(
                self.slide_window_chunk(
                    input, self.split_length, self.window_length
                )
            )
        return cutted
