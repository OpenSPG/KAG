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

from typing import Type, List
from kag.interface import SplitterABC
from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.common.utils import generate_hash_id
from knext.common.base.runnable import Input, Output
from kag.builder.component.splitter.base_table_splitter import BaseTableSplitter


@SplitterABC.register("length")
@SplitterABC.register("length_splitter")
class LengthSplitter(BaseTableSplitter):
    """
    A class for splitting text based on length.

    This class inherits from BaseTableSplitter and provides the functionality to split text
    into smaller chunks based on a specified length and window size. It also handles table data
    by splitting it into smaller markdown tables.

    Attributes:
        split_length (int): The maximum length of each chunk.
        window_length (int): The length of the overlap between chunks.
    """

    def __init__(
        self,
        split_length: int = 500,
        window_length: int = 100,
        strict_length: bool = False,
        **kwargs,
    ):
        """
        Initializes the LengthSplitter with the specified split length and window length.

        Args:
            split_length (int): The maximum length of each chunk. Defaults to 500.
            window_length (int): The length of the overlap between chunks. Defaults to 100.
            strict_length (bool): Whether to split strictly by length without preserving sentences. Defaults to False.
        """
        super().__init__(**kwargs)
        self.split_length = split_length
        self.window_length = window_length
        self.strict_length = strict_length

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return Chunk

    def chunk_breakdown(self, chunk):
        chunks = self.logic_break(chunk)
        if chunks:
            res_chunks = []
            for c in chunks:
                res_chunks.extend(self.chunk_breakdown(c))
        else:
            res_chunks = self.slide_window_chunk(
                chunk, self.split_length, self.window_length
            )
        return res_chunks

    def logic_break(self, chunk):
        return None

    def split_sentence(self, content):
        """
        Splits the given content into sentences based on delimiters.

        Args:
            content (str): The content to be split into sentences.

        Returns:
            List[str]: A list of sentences.
        """
        sentence_delimiters = (
            ".。？?！!" if self.kag_project_config.language == "en" else "。？！"
        )
        output = []
        start = 0
        for idx, char in enumerate(content):
            if char in sentence_delimiters:
                end = idx
                tmp = content[start : end + 1].strip()
                if len(tmp) > 0:
                    output.append(tmp.strip())
                start = idx + 1
        res = content[start:].strip()
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
            table_chunks = self.split_table(
                org_chunk=org_chunk, chunk_size=chunk_size, sep=sep
            )
            if table_chunks is not None:
                return table_chunks

        # 如果启用严格长度切分，不按句子切分
        if getattr(self, "strict_length", False):
            return self.strict_length_chunk(org_chunk)

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
            if idx > 0:
                new_id = generate_hash_id(f"{org_chunk.id}#{idx}")
                new_name = f"{org_chunk.name}_split_{idx}"
            else:
                new_id = org_chunk.id
                new_name = org_chunk.name

            chunk = Chunk(
                id=new_id,
                name=new_name,
                content=sep.join(sentences),
                type=org_chunk.type,
                chunk_size=chunk_size,
                window_length=window_length,
                **org_chunk.kwargs,
            )
            output.append(chunk)
        return output

    def strict_length_chunk(
        self,
        org_chunk: Chunk,
    ) -> List[Chunk]:
        """
        Splits the content into chunks strictly by length without preserving sentence boundaries.

        Args:
            org_chunk (Chunk): The original chunk to be split.
            chunk_size (int, optional): The maximum size of each chunk. Defaults to 2000.
            window_length (int, optional): The length of the overlap between chunks. Defaults to 300.

        Returns:
            List[Chunk]: A list of Chunk objects.
        """
        content = org_chunk.content
        total_length = len(content)
        output = []

        position = 0
        chunk_index = 0

        while position < total_length:
            # 计算当前chunk的内容
            chunk_content = content[position : position + self.split_length]

            # 创建新的Chunk对象
            chunk = Chunk(
                id=generate_hash_id(f"{org_chunk.id}#{chunk_index}"),
                name=f"{org_chunk.name}_split_{chunk_index}",
                content=chunk_content,
                type=org_chunk.type,
                chunk_size=self.split_length,
                window_length=self.window_length,
                **org_chunk.kwargs,
            )
            output.append(chunk)

            # 更新位置和索引
            position = position + self.split_length - self.window_length
            chunk_index += 1

            # 确保不会出现负索引
            if position < 0:
                position = 0

        return output

    def _invoke(self, input: Chunk, **kwargs) -> List[Output]:
        """
        Invokes the splitting of the input chunk based on the specified length and window size.

        Args:
            input (Chunk): The chunk(s) to be split.
            **kwargs: Additional keyword arguments, currently unused but kept for potential future expansion.

        Returns:
            List[Output]: A list of Chunk objects resulting from the split operation.
        """
        cutted = []
        if isinstance(input, list):
            for item in input:
                cutted.extend(
                    self.slide_window_chunk(item, self.split_length, self.window_length)
                )
        else:
            cutted.extend(
                self.slide_window_chunk(input, self.split_length, self.window_length)
            )
        return cutted
