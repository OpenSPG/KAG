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

from knext.common.base.runnable import Input, Output

from kag.builder.model.chunk import Chunk
from kag.builder.model.chunk import ChunkTypeEnum
from kag.builder.prompt.outline_prompt import OutlinePrompt
from kag.interface.builder import SplitterABC

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
        chunks = self.sep_by_outline_ignore_duplicates(
            content, outlines, org_chunk=chunk
        )
        return chunks

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

    def unify_outline_levels(outlines):
        """
        统一相同类型标题的级别，如 "第一节" 和 "第二节" 应有相同的层级。

        Args:
            outlines (list): 提取的标题列表，格式为 [(标题文本, 级别), ...]。

        Returns:
            list: 调整后的标题列表，格式同输入。
        """
        if not outlines:
            return []

        # 辅助函数：判断标题是否属于同类型
        def is_same_type(title1, title2):
            """
            判断两个标题是否属于同一类型。
            """
            # 检查是否包含 "章" 或 "节"，并判断编号相似
            keywords = ["章", "节", "部分", "篇"]
            for keyword in keywords:
                if keyword in title1 and keyword in title2:
                    return True
            return False

        # 建立类型到级别的映射
        type_to_level = {}
        for title, level in outlines:
            for keyword in ["章", "节", "部分", "篇"]:
                if keyword in title:
                    type_to_level.setdefault(keyword, level)

        # 调整级别
        unified_outlines = []
        for title, level in outlines:
            for keyword in ["章", "节", "部分", "篇"]:
                if keyword in title and keyword in type_to_level:
                    level = type_to_level[keyword]
                    break
            unified_outlines.append((title, level))

        return unified_outlines

    def sep_by_outline(self, content, outlines):
        """
        按层级划分内容为 chunks，剔除无效的标题。
        """
        # 过滤无效的 outlines
        outlines = self.filter_outlines(outlines)
        outlines = self.unify_outline_levels(outlines)

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
                **org_chunk.kwargs,
            )
            output.append(chunk)
        return output

    def sep_by_outline_ignore_duplicates(
        self, content, outlines, min_length=50, max_length=500, org_chunk=None
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

        if not outlines or len(outlines) == 0:
            cutted = []
            if isinstance(org_chunk, list):
                for item in org_chunk:
                    cutted.extend(self.slide_window_chunk(item))
            return cutted

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

            # add origin kwargs
            kwargs = {}
            for key, value in org_chunk[0].kwargs.items():
                kwargs[f"origin_{key}"] = value

            chunk = Chunk(
                id=Chunk.generate_hash_id(f"{full_path}#{idx}"),
                name=full_path,
                content=chunk_content,
                kwargs=kwargs,
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

        for idx, chunk in enumerate(merged_chunks):
            chunk.prev_content = merged_chunks[idx - 1].content if idx > 0 else None
            chunk.next_content = (
                merged_chunks[idx + 1].content if idx < len(merged_chunks) - 1 else None
            )

        return merged_chunks

    def invoke(self, input: Input, **kwargs) -> List[Chunk]:
        chunks = self.outline_chunk(input)
        return chunks


if __name__ == "__main__":
    from kag.builder.component.splitter.length_splitter import LengthSplitter
    from kag.builder.component.splitter.outline_splitter import OutlineSplitter
    from kag.builder.component.reader.txt_reader import TXTReader
    from kag.common.env import init_kag_config

    init_kag_config(
        os.path.join(
            os.path.dirname(__file__),
            "../../../../tests/builder/component/test_config.cfg",
        )
    )
    docx_reader = DocxReader()
    length_splitter = LengthSplitter(split_length=8000)
    outline_splitter = OutlineSplitter()
    txt_path = os.path.join(
        os.path.dirname(__file__), "../../../../tests/builder/data/儿科学_short.txt"
    )
    docx_path = "/Users/zhangxinhong.zxh/Downloads/waikexue_short.doc"
    # chain = docx_reader >> length_splitter >> outline_splitter
    chunk = docx_reader.invoke(docx_path)
    chunks = length_splitter.invoke(chunk)
    chunks = outline_splitter.invoke(chunks)
    print(chunks)
