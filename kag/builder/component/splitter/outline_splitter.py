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
from typing import List, Type, Union, Tuple

from knext.common.base.runnable import Input, Output

from kag.builder.model.chunk import Chunk, dump_chunks
from kag.builder.model.chunk import ChunkTypeEnum
from kag.builder.prompt.outline_prompt import OutlinePrompt
from kag.builder.prompt.outline_align_prompt import OutlineAlignPrompt
from kag.interface.builder import SplitterABC
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import collections
import matplotlib.pyplot as plt


logger = logging.getLogger(__name__)


class OutlineSplitter(SplitterABC):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm = self._init_llm()
        language = os.getenv("KAG_PROMPT_LANGUAGE", "zh")
        self.prompt = OutlinePrompt(language)
        self.min_length = kwargs.get("min_length", 100)
        self.workers = kwargs.get("workers", 32)
        self.chunk_size = kwargs.get("chunk_size", 500)
        self.llm_max_tokens = kwargs.get("llm_max_tokens", 10240)

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return Chunk

    def build_catalog_tree(self, outlines_with_content):
        catalog_tree = []
        stack = []  # 用于跟踪当前的节点层级，格式为 [(title, level, node), ...]

        for title, content, level in outlines_with_content:
            # 找到正确的父节点
            while stack and stack[-1][1] >= level:  # 父节点的级别应该更高（数字更小）
                stack.pop()

            # # 创建新节点
            # # title应该拼上所有父节点的title
            # if stack:
            #     # only add title if stack level
            #     title = "/".join([item[0] for item in stack] + [title])
            node = {"title": title, "content": content, "children": []}

            # 如果栈为空，或者当前节点的级别高于栈顶节点的级别，说明当前节点是根节点或新的分支节点
            if not stack or stack[-1][1] >= level:
                if stack:
                    stack[-1][2]["children"].append(
                        node
                    )  # 将新节点添加到最近的父节点的 children 列表中
                else:
                    catalog_tree.append(node)  # 如果栈为空，说明这是一个根节点
            else:
                # 将新节点添加到找到的父节点的 children 列表中
                stack[-1][2]["children"].append(node)

            # 将新节点和其级别、标题添加到 stack 中，以便后续添加子节点
            stack.append((title, level, node))

        return catalog_tree

    def simplify_catalog_tree(self, node, parent=None, parent_content_length=0):
        # 首先递归处理所有子节点
        for child in list(node["children"]):  # 使用 list 来复制列表，以便在迭代时修改它
            self.simplify_catalog_tree(child, node, len(node["content"]))

        # 然后检查当前节点是否可以与父节点合并
        content_length = len(node["content"])
        if content_length + parent_content_length <= self.chunk_size and parent:
            # 如果当前节点的内容长度加上父节点的内容长度不超过阈值，则合并
            parent["content"] += " " + node["content"]
            # 将当前节点的子节点添加到父节点的子节点列表中
            parent["children"].extend(node["children"])
            # 从父节点的子节点列表中移除当前节点
            parent["children"].remove(node)
            return  # 停止进一步处理

    def outline_chunk(self, chunk: Union[Chunk, List[Chunk]]) -> List[Chunk]:
        if isinstance(chunk, Chunk):
            chunk = [chunk]
        outlines = []
        for c in chunk:
            outline = self.llm.invoke(
                {"input": c.content, "current_outline": outlines}, self.prompt
            )
            # 过滤无效的 outlines
            outline = self.filter_outlines(outline)
            outlines.extend(outline)
        content = "\n".join([c.content for c in chunk])
        # chunks = self.sep_by_outline_ignore_duplicates(
        #     content, outlines, org_chunk=chunk
        # )
        chunks = self.sep_by_outline_with_outline_tree(
            content, outlines, org_chunk=chunk
        )
        return chunks

    def process_batch(self, batch: List[Chunk]) -> List[Tuple[str, int]]:
        """
        处理单个批次的文档块

        Args:
            batch: List[Chunk] 待处理的文档块

        Returns:
            List[Tuple[str, int]] 提取的outline列表
        """
        outlines = []
        current_outlines = []

        for c in batch:
            # 传入当前已提取的outlines作为上下文
            outline = self.llm.invoke(
                {"input": c.content, "current_outline": current_outlines}, self.prompt
            )

            # 过滤无效的outlines
            valid_outlines = self.filter_outlines(outline)
            outlines.extend(valid_outlines)
            current_outlines.extend(valid_outlines)

        return outlines

    def align_outlines(self, outlines):
        """
        使用LLM对齐提取的outline层级

        Args:
            outlines: List[Tuple[str, int]] 原始outline列表

        Returns:
            List[Tuple[str, int]] 对齐后的outline列表
        """
        if not outlines:
            return []

        # 初始化align prompt
        language = os.getenv("KAG_PROMPT_LANGUAGE", "zh")
        align_prompt = OutlineAlignPrompt(language)

        # 使用LLM对齐outline
        try:
            aligned_outlines = self.llm.invoke({"outlines": outlines}, align_prompt)
            logger.info("Successfully aligned outlines using LLM")
            return aligned_outlines
        except Exception as e:
            logger.error(f"Error aligning outlines with LLM: {str(e)}")
            # 如果LLM对齐失败,回退到规则based对齐
            return self._rule_based_align(outlines)

    def _rule_based_align(self, outlines):
        """
        基于规则的outline对齐(作为备选方案)
        """
        # 保留原有的基于规则的对齐逻辑作为备选
        title_patterns = {
            "chapter": r"第[一二三四五六七八九十\d]+章",
            "section": r"第[一二三四五六七八九十\d]+节",
            "part": r"第[一二三四五六七八九十\d]+部分",
            "article": r"第[一二三四五六七八九十\d]+条",
        }

        pattern_levels = {"chapter": 1, "section": 2, "part": 1, "article": 3}

        aligned_outlines = []
        for title, level in outlines:
            matched_pattern = None
            for pattern_type, pattern in title_patterns.items():
                if re.search(pattern, title):
                    matched_pattern = pattern_type
                    break

            if matched_pattern:
                aligned_level = pattern_levels[matched_pattern]
            else:
                aligned_level = level

            aligned_outlines.append((title, aligned_level))

        return aligned_outlines

    def outline_chunk_batch(self, chunk: List[Chunk]) -> List[Chunk]:
        """
        批量处理文档块并提取大纲

        Args:
            chunk: List[Chunk] 输入的文档块列表

        Returns:
            List[Chunk] 处理后的文档块列表
        """
        assert isinstance(chunk, list)
        self.batch_size = len(chunk) // self.workers if len(chunk) > self.workers else 1

        outlines = []
        # 将 chunk 分成多个批次,这里注意，为了保证outline抽取的连续行，每个batch需要连续的chunk
        batches = [
            chunk[i : i + self.batch_size]
            for i in range(0, len(chunk), self.batch_size)
        ]

        mapping = {}
        futures = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # 提交每个批次到线程池
            for idx, batch in enumerate(batches):
                future = executor.submit(self.process_batch, batch)
                mapping[future] = idx
                futures.append(future)

            results = [0] * len(batches)
            # 等待所有批次完成并收集结果
            for future in as_completed(futures):
                results[mapping[future]] = future.result()
                logger.info(f"outline batch{mapping[future]} done")

        for result in results:
            outlines.extend(result)

        content = "\n".join([c.content for c in chunk])

        aligned_outlines = self.align_outlines(outlines)
        # 使用对齐后的outlines进行分块
        chunks = self.sep_by_outline_with_outline_tree(
            content, aligned_outlines, org_chunk=chunk
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

    def unify_outline_levels(self, outlines):
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
                id=Chunk.generate_hash_id(f"{org_chunk.id}#{idx}"),
                name=f"{org_chunk.name}#{idx}",
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
                # 检查position_check是否为空或者当前start是否大于上一个元素的start
                if not position_check or start > position_check[-1][1]:
                    position_check.append((outline, start))
                else:
                    # 如果当前start不大于上一个元素的start，则跳过这个元素
                    continue
                seen_titles.add(title)

        if not position_check:
            return []

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
            origin_properties = {}
            for key, value in org_chunk[0].kwargs.items():
                origin_properties[key] = value

            chunk = Chunk(
                id=Chunk.generate_hash_id(f"{full_path}#{idx}"),
                name=full_path,
                content=chunk_content,
                **origin_properties,
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

    def sep_by_outline_with_outline_tree(self, content, outlines, org_chunk=None):
        """
        按层级划分内容为 chunks，剔除无效的标题，并忽略重复的标题。

        参数：
        - content: str，完整���容。
        - outlines: List[Tuple[str, int]]，每个标题及其层级的列表。
        - min_length: int，chunk 的最小长度，低于此值时尝试合并。
        - max_length: int，chunk 的最大长度，合并后不能超过此值。

        返回：
        - List[Chunk]，分割后的 chunk 列表。
        """

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
                # 检查position_check是否为空或者当前start是否大于上一个元素的start
                if not position_check or start > position_check[-1][1]:
                    position_check.append((outline, start))
                else:
                    # 如果当前start不大于上一个元素的start，则跳过这个元素
                    continue
                seen_titles.add(title)

        for idx, (outline, start) in enumerate(position_check):
            title, level = outline
            end = (
                position_check[idx + 1][1]
                if idx + 1 < len(position_check)
                else len(content)
            )
            position_check[idx] = (outline, start, end)

        outlines_with_content = []
        for outline, start, end in position_check:
            title, level = outline
            t_content = content[start:end]
            outlines_with_content.append((title, t_content, level))

        # 构建目录树
        catalog_tree = self.build_catalog_tree(outlines_with_content)

        # 简化目录树
        # if catalog_tree:
        #     for node in catalog_tree:
        #         self.simplify_catalog_tree(node)

        # add origin kwargs
        origin_properties = {}
        for key, value in org_chunk[0].kwargs.items():
            origin_properties[key] = value

        def generate_chunks(node, chunks=None, parent_title=""):
            if chunks is None:
                chunks = []

            # 构建当前节点的完整title
            full_title = (
                "/".join([parent_title, node["title"]])
                if parent_title
                else node["title"]
            )

            # 为当前节点生成chunk
            chunk_id = Chunk.generate_hash_id(full_title)  # 使用完整title生成ID
            chunk = Chunk(
                id=chunk_id,
                name=full_title,  # 使用完整title
                content=node["content"],
                # 假设origin_properties是全局的或者在函数外部定义的，包含其他需要的属性
                **origin_properties,
            )
            chunks.append(chunk)

            # 递归为子节点生成chunk
            for child in node.get("children", []):
                generate_chunks(
                    child, chunks, full_title
                )  # 将当前完整title传递给子节点

            return chunks

        chunks = []
        for node in catalog_tree:
            chunks.extend(generate_chunks(node))
        # 合并过短的 chunks
        merged_chunks = []
        buffer = None

        for chunk in chunks:
            if buffer:
                # 当前 chunk 合并到 buffer 中
                if (
                    chunk.name.startswith(buffer.name)  # 同一父级目录
                    and len(buffer.content) + len(chunk.content) <= self.chunk_size
                ):
                    buffer.content += chunk.content
                    continue
                else:
                    merged_chunks.append(buffer)
                    buffer = None

            if len(chunk.content) < self.min_length:
                # 缓存过短的 chunk
                buffer = chunk
            else:
                # 长度足够，直接加入结果
                merged_chunks.append(chunk)

        # 如果最后一个 chunk 被缓存在 buffer，直接加入结果
        if buffer:
            merged_chunks.append(buffer)

        for i in range(len(merged_chunks) - 1, -1, -1):
            chunk = merged_chunks[i]
            if len(chunk.content) < (self.min_length * 0.5):
                del merged_chunks[i]

        for idx, chunk in enumerate(merged_chunks):
            chunk.prev_content = merged_chunks[idx - 1].content if idx > 0 else None
            chunk.next_content = (
                merged_chunks[idx + 1].content if idx < len(merged_chunks) - 1 else None
            )

        return merged_chunks

    def log(self, chunks, log_path="./chunk_log.txt"):
        length_counts = collections.defaultdict(int)

        for chunk in chunks:
            length = len(chunk.content)
            length_segment = length // 10
            length_counts[length_segment] += 1

        with open(log_path, "a") as f:
            for length_segment, count in length_counts.items():
                f.write(
                    f"Length segment {length_segment*10}-{(length_segment+1)*10} chunks: {count}\n"
                )

        # 绘制长度分布图
        self.plot_length_distribution(length_counts)

    def plot_length_distribution(self, length_counts):
        segments = list(length_counts.keys())
        counts = list(length_counts.values())

        plt.figure(figsize=(10, 6))
        plt.bar(segments, counts, color="blue")
        plt.xlabel("Length Segment")
        plt.ylabel("Number of Chunks")
        plt.title("Chunk Length Distribution")
        plt.xticks(segments)
        plt.savefig("chunk_length_distribution.png")

    def splitter_chunk(self, input: Input, **kwargs) -> List[Chunk]:
        cutted = []
        chunk_size = kwargs.get("chunk_size")
        if isinstance(input, list):
            for item in input:
                cutted.extend(self.slide_window_chunk(item, chunk_size=chunk_size))
        else:
            cutted.extend(self.slide_window_chunk(input, chunk_size=chunk_size))
        return cutted

    def invoke(self, input: Input, **kwargs) -> List[Chunk]:
        chunks = self.splitter_chunk(input, chunk_size=self.llm_max_tokens // 2)
        chunks = self.outline_chunk_batch(chunks)
        chunks = self.splitter_chunk(chunks, chunk_size=self.chunk_size)
        # self.log(chunks)
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
    docx_reader = DocxReader()
    txt_reader = TXTReader()
    length_splitter = LengthSplitter(split_length=5000)
    outline_splitter = OutlineSplitter()
    txt_path = os.path.join(
        os.path.dirname(__file__), "../../../../tests/builder/data/儿科学_short.txt"
    )
    docx_path = "/Users/zhangxinhong.zxh/Downloads/waikexue_short.docx"
    test_dir = "/Users/zhangxinhong.zxh/Downloads/1127_medkag_book"
    files = [
        os.path.join(test_dir, file)
        for file in os.listdir(test_dir)
        if file.endswith(".docx")
    ]
    files = [
        files[0],
    ]

    def process_file(file):
        chain = docx_reader >> outline_splitter
        chunks = chain.invoke(file, max_workers=10)
        dump_chunks(chunks, output_path=file.replace(".docx", ".json"))

    def process_file_without_chain(file):
        chunk = docx_reader.invoke(file)
        chunks = outline_splitter.invoke(chunk)
        dump_chunks(chunks, output_path=file.replace(".docx", ".json"))

    # with ThreadPoolExecutor(max_workers=10) as executor:
    #     futures = [executor.submit(process_file, file) for file in files]

    # for future in as_completed(futures):
    #     print(future.result())

    process_file_without_chain(docx_path)

    # chunk = docx_reader.invoke(docx_path)
    # chunk = txt_reader.invoke(txt_path)
    # chunks = length_splitter.invoke(chunk)
    # chunks = outline_splitter.invoke(chunks)
    # print(chunks)
