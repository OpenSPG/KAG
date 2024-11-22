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
from typing import List, Type, Union

from kag.interface.builder import SplitterABC
from kag.builder.prompt.outline_prompt import OutlinePrompt
from kag.builder.model.chunk import Chunk
from knext.common.base.runnable import Input, Output
from kag.common.llm.client.llm_client import LLMClient

logger = logging.getLogger(__name__)


class OutlineSplitter(SplitterABC):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm = self._init_llm()
        language = os.getenv("KAG_PROMPT_LANGUAGE", "zh")
        self.prompt = OutlinePrompt(language)

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return Chunk

    def outline_chunk(self, chunk: Union[Chunk, List[Chunk]]) -> List[Chunk]:
        if isinstance(chunk, Chunk):
            chunk = [chunk]
        outlines = []
        for c in chunk:
            outline = self.llm.invoke({"input": c.content}, self.prompt)
            outlines.extend(outline)
        content = "\n".join([c.content for c in chunk])
        chunks = self.sep_by_outline_ignore_duplicates(content, outlines)
        return chunks

    import re

    def filter_outlines(self, raw_outlines):
        """
        过滤掉无效的标题，包括仅由数字、罗马数字、中文数字以及与数字相关的标点组合构成的标题。
        """
        # 匹配阿拉伯数字、中文数字、罗马数字和无效标点组合
        invalid_pattern = r"""
            ^                      # 匹配开头
            [0-9一二三四五六七八九十零IIVXLCDM\-.\(\)\[\]\s]*  # 阿拉伯数字、中文数字、罗马数字及常见修饰符
            $                      # 匹配结尾
        """
        valid_outlines = []
        for title, level in raw_outlines:
            # 去掉两侧的空白符，避免干扰
            title = title.strip()
            # 过滤无效标题
            if re.fullmatch(invalid_pattern, title, re.VERBOSE):
                continue
            # 保留有效标题
            valid_outlines.append((title, level))
        return valid_outlines

    def sep_by_outline(self, content, outlines):
        """
        按层级划分内容为 chunks，剔除无效的标题。
        """
        # 过滤无效的 outlines
        outlines = self.filter_outlines(outlines)

        position_check = []
        for outline in outlines:
            start = content.find(outline[0])
            if start != -1:
                position_check.append((outline, start))

        if not position_check:
            return []  # 如果没有找到任何标题，返回空

        chunks = []
        father_stack = []

        for idx, (outline, start) in enumerate(position_check):
            title, level = outline
            end = (
                position_check[idx + 1][1]
                if idx + 1 < len(position_check)
                else len(content)
            )
            while father_stack and father_stack[-1][1] >= level:
                father_stack.pop()
            full_path = "/".join([item[0] for item in father_stack] + [title])
            chunk_content = content[start:end]
            chunk = Chunk(
                id=Chunk.generate_hash_id(f"{full_path}#{idx}"),
                name=full_path,
                content=chunk_content,
            )
            chunks.append(chunk)
            father_stack.append((title, level))

        return chunks

    def sep_by_outline_with_merge(
        self, content, outlines, min_length=200, max_length=5000
    ):
        """
        按层级划分内容为 chunks，并对过短的 chunk 尝试进行合并，控制合并后长度。

        参数：
        - content: str，完整内容。
        - outlines: List[Tuple[str, int]]，每个标题及其层级的列表。
        - min_length: int，chunk 的最小长度，低于此值时尝试合并。
        - max_length: int，chunk 的最大长度，合并后不能超过此值。

        返回：
        - List[Chunk]，分割后的 chunk 列表。
        """
        # 过滤无效的 outlines
        outlines = self.filter_outlines(outlines)

        position_check = []
        for outline in outlines:
            start = content.find(outline[0])
            if start != -1:
                position_check.append((outline, start))

        if not position_check:
            return []  # 如果没有找到任何标题，返回空

        chunks = []
        father_stack = []

        for idx, (outline, start) in enumerate(position_check):
            title, level = outline
            end = (
                position_check[idx + 1][1]
                if idx + 1 < len(position_check)
                else len(content)
            )
            while father_stack and father_stack[-1][1] >= level:
                father_stack.pop()
            full_path = "/".join([item[0] for item in father_stack] + [title])
            chunk_content = content[start:end]
            chunk = Chunk(
                id=Chunk.generate_hash_id(f"{full_path}#{idx}"),
                name=full_path,
                content=chunk_content,
            )
            chunks.append(chunk)
            father_stack.append((title, level))

        # 合并过短的 chunks
        merged_chunks = []
        buffer = None

        for chunk in chunks:
            if buffer:
                # 当前 chunk 合并到 buffer 中
                if (
                    chunk.name.startswith(buffer.name)  # 同一父级目录
                    and len(buffer.content) + len(chunk.content) <= max_length
                ):
                    buffer.content += chunk.content
                    buffer.name = buffer.name  # 名称不变，保持父级目录路径
                    continue
                else:
                    merged_chunks.append(buffer)
                    buffer = None

            if len(chunk.content) < min_length:
                # 缓存过短的 chunk
                buffer = chunk
            else:
                # 长度足够，直接加入结果
                merged_chunks.append(chunk)

        # 如果最后一个 chunk 被缓存在 buffer，直接加入结果
        if buffer:
            merged_chunks.append(buffer)

        return merged_chunks

    def sep_by_outline_ignore_duplicates(
        self, content, outlines, min_length=50, max_length=500
    ):
        """
        按层级划分内容为 chunks，剔除无效的标题，并忽略重复的标题。

        参数：
        - content: str，完整内容。
        - outlines: List[Tuple[str, int]]，每个标题及其层级的列表。
        - min_length: int，chunk 的最小长度，低于此值时尝试合并。
        - max_length: int，chunk 的最大长度，合并后不能超过此值。

        返回：
        - List[Chunk]，分割后的 chunk 列表。
        """
        # 过滤无效的 outlines
        outlines = self.filter_outlines(outlines)

        position_check = []
        seen_titles = set()
        for outline in outlines:
            title, level = outline
            start = content.find(title)
            if start != -1 and title not in seen_titles:
                # 如果标题未重复，则加入 position_check
                position_check.append((outline, start))
                seen_titles.add(title)

        if not position_check:
            return []  # 如果没有找到任何标题，返回空

        chunks = []
        father_stack = []

        for idx, (outline, start) in enumerate(position_check):
            title, level = outline
            end = (
                position_check[idx + 1][1]
                if idx + 1 < len(position_check)
                else len(content)
            )
            while father_stack and father_stack[-1][1] >= level:
                father_stack.pop()
            full_path = "/".join([item[0] for item in father_stack] + [title])
            chunk_content = content[start:end]
            chunk = Chunk(
                id=Chunk.generate_hash_id(f"{full_path}#{idx}"),
                name=full_path,
                content=chunk_content,
            )
            chunks.append(chunk)
            father_stack.append((title, level))

        # 合并过短的 chunks
        merged_chunks = []
        buffer = None

        for chunk in chunks:
            if buffer:
                # 当前 chunk 合并到 buffer 中
                if (
                    chunk.name.startswith(buffer.name)  # 同一父级目录
                    and len(buffer.content) + len(chunk.content) <= max_length
                ):
                    buffer.content += chunk.content
                    continue
                else:
                    merged_chunks.append(buffer)
                    buffer = None

            if len(chunk.content) < min_length:
                # 缓存过短的 chunk
                buffer = chunk
            else:
                # 长度足够，直接加入结果
                merged_chunks.append(chunk)

        # 如果最后一个 chunk 被缓存在 buffer，直接加入结果
        if buffer:
            merged_chunks.append(buffer)

        return merged_chunks

    def invoke(self, input: Input, **kwargs) -> List[Chunk]:
        chunks = self.outline_chunk(input)
        return chunks


if __name__ == "__main__":
    from kag.builder.component.splitter.length_splitter import LengthSplitter
    from kag.builder.component.splitter.outline_splitter import OutlineSplitter
    from kag.builder.component.reader.docx_reader import DocxReader
    from kag.builder.component.reader.txt_reader import TXTReader
    from kag.common.env import init_kag_config

    init_kag_config(
        os.path.join(
            os.path.dirname(__file__),
            "../../../../tests/builder/component/test_config.cfg",
        )
    )
    docx_reader = TXTReader()
    length_splitter = LengthSplitter(split_length=8000)
    outline_splitter = OutlineSplitter()
    docx_path = os.path.join(
        os.path.dirname(__file__), "../../../../tests/builder/data/儿科学_short.txt"
    )
    # chain = docx_reader >> length_splitter >> outline_splitter
    chunk = docx_reader.invoke(docx_path)
    chunks = length_splitter.invoke(chunk)
    chunks = outline_splitter.invoke(chunks)
    print(chunks)
