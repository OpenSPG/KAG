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
import collections
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Type, Union, Tuple

import matplotlib.pyplot as plt
from kag.interface.common.prompt import PromptABC
from knext.common.base.runnable import Input, Output
from kag.common.utils import generate_hash_id
from kag.builder.model.chunk import Chunk, dump_chunks
from kag.builder.model.chunk import ChunkTypeEnum
from kag.builder.prompt.outline_align_prompt import OutlineAlignPrompt
from kag.interface import SplitterABC
from kag.interface import LLMClient

logger = logging.getLogger(__name__)


@SplitterABC.register("outline")
@SplitterABC.register("outline_splitter")
class OutlineSplitter(SplitterABC):
    def __init__(
        self,
        llm: LLMClient,
        min_length: int = 100,
        workers: int = 10,
        chunk_size: int = 500,
        llm_max_tokens: int = 8000,
        align_parallel: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm = llm
        self.prompt = PromptABC.from_config(
            {"type": "outline", "language": self.kag_project_config.language}
        )
        self.min_length = min_length
        self.workers = workers
        self.chunk_size = chunk_size
        self.llm_max_tokens = llm_max_tokens
        self.align_parallel = align_parallel

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return Chunk

    def build_catalog_tree(self, outlines_with_content):
        catalog_tree = []
        stack = []  # 用于跟踪当前的节点层级，格式为 [(title, level, node), ...]

        for title, content, sd_content, level in outlines_with_content:
            # 找到正确的父节点
            while stack and stack[-1][1] >= level:  # 父节点的级别应该更高（数字更小）
                stack.pop()

            # # 创建新节点
            # # title应该拼上所有父节点的title
            # if stack:
            #     # only add title if stack level
            #     title = "/".join([item[0] for item in stack] + [title])
            node = {
                "title": title,
                "content": content,
                "children": [],
                "start": sd_content[0],
                "end": sd_content[1],
            }

            # 如果栈为空，或者当前节点的级别高于栈顶节点的级别，说明当前节点是根节点或新的分支节点
            if not stack or stack[-1][1] >= level:
                if stack:
                    stack[-1][2]["children"].append(node)  # 将新节点添加到最近的父节点的 children 列表中
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
            # paralle模式可以用量大的outline: 暂时没有好的方法:TODO
            if self.align_parallel:
                valid_outlines = self.filter_outlines_parallel(outline)
            else:
                valid_outlines = self.filter_outlines(outline)
            outlines.extend(valid_outlines)
            current_outlines.extend(valid_outlines)

        return outlines

    def align_outlines(self, outlines):
        """
        使用LLM对齐提取的outline层级，使用前一个对齐完成的batch的后30%作为交叉部分

        Args:
            outlines: List[Tuple[str, int]] 原始outline列表

        Returns:
            List[Tuple[str, int]] 对齐后的outline列表
        """
        if not outlines:
            return []

        # 初始化align prompt
        align_prompt = PromptABC.from_config(
            {"type": "outline_align", "language": self.kag_project_config.language}
        )

        max_length = 4000

        try:
            # 处理第一个batch
            current_batch = []
            aligned_outlines = []

            for outline in outlines:
                # 计算添加当前outline后的总字符串长度
                test_batch = current_batch + [outline]
                batch_str = str(test_batch)  # 将整个batch转换为字符串计算长度

                if len(batch_str) <= max_length:
                    current_batch.append(outline)
                else:
                    break

            # 对齐第一个batch
            if current_batch:
                aligned_batch = self.llm.invoke(
                    {"outlines": current_batch}, align_prompt
                )
                aligned_outlines.extend(aligned_batch)
                last_aligned = aligned_batch

                # 处理剩余的outlines
                remaining_outlines = outlines[len(current_batch) :]

                while remaining_outlines:
                    # 获取前一个batch最后30%的内容作为交叉部分
                    overlap_count = max(1, len(last_aligned) * 30 // 100)
                    overlap_part = last_aligned[-overlap_count:]

                    # 构建新batch
                    current_batch = []

                    # 添加新的outlines直到达到长度限制
                    for outline in remaining_outlines:
                        test_batch = overlap_part + current_batch + [outline]
                        batch_str = str(test_batch)

                        if len(batch_str) <= max_length:
                            current_batch.append(outline)
                        else:
                            break

                    if not current_batch:
                        # 如果无法添加任何新outline，说明单个outline太长，需要特殊处理
                        logger.warning(
                            "Single outline too long, processing individually"
                        )
                        current_batch = [remaining_outlines[0]]

                    # 对齐当前batch（包含交叉部分）
                    full_batch = overlap_part + current_batch
                    aligned_batch = self.llm.invoke(
                        {"outlines": full_batch}, align_prompt
                    )

                    # 只保留非交叉部分的结果
                    aligned_outlines.extend(aligned_batch[overlap_count:])
                    last_aligned = aligned_batch

                    # 更新remaining_outlines
                    remaining_outlines = remaining_outlines[len(current_batch) :]

            return aligned_outlines

        except Exception as e:
            logger.error(f"Error aligning outlines with LLM: {str(e)}")
            return self._rule_based_align(outlines)

    def align_outlines_parallel(self, outlines):
        """
        并行处理outline对齐，每个batch与相邻batch有30%的交叉部分

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
        max_length = 8000

        try:
            # 将outlines分成多个batch，每个batch最大长度不超过max_length
            batches = []
            current_batch = []

            for outline in outlines:
                test_batch = current_batch + [outline]
                batch_str = str(test_batch)

                if len(batch_str) <= max_length:
                    current_batch.append(outline)
                else:
                    if current_batch:
                        batches.append(current_batch)
                    current_batch = [outline]

            if current_batch:
                batches.append(current_batch)

            # 并行处理每个batch
            futures = []
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                for i, batch in enumerate(batches):
                    # 获取与前一个batch的交叉部分
                    prev_overlap = []
                    if i > 0:
                        prev_batch = batches[i - 1]
                        overlap_count = max(1, len(prev_batch) * 30 // 100)
                        prev_overlap = prev_batch[-overlap_count:]

                    # 获取与后一个batch的交叉部分
                    next_overlap = []
                    if i < len(batches) - 1:
                        next_batch = batches[i + 1]
                        overlap_count = max(1, len(next_batch) * 30 // 100)
                        next_overlap = next_batch[:overlap_count]

                    # 构建完整的batch（包含交叉部分）
                    full_batch = prev_overlap + batch + next_overlap

                    # 提交任务到线程池
                    future = executor.submit(
                        self.llm.invoke, {"outlines": full_batch}, align_prompt
                    )
                    futures.append((i, future, len(prev_overlap), len(next_overlap)))

            # 收集结果并按原始顺序合并
            results = [None] * len(batches)
            for i, future, prev_len, next_len in futures:
                try:
                    aligned_batch = future.result()
                    # 只保留非交叉部分
                    results[i] = aligned_batch[prev_len : len(aligned_batch) - next_len]
                except Exception as e:
                    logger.error(f"Error processing batch {i}: {str(e)}")
                    # 如果处理失败，使用规则based对齐处理该batch
                    results[i] = self._rule_based_align(batches[i])

            # 合并所有结果
            aligned_outlines = []
            for batch_result in results:
                aligned_outlines.extend(batch_result)

            return aligned_outlines

        except Exception as e:
            logger.error(f"Error aligning outlines with LLM: {str(e)}")
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
                # logger.info(f"outline batch{mapping[future]} done")

        for result in results:
            outlines.extend(result)

        content = "\n".join([c.content for c in chunk])

        if self.align_parallel:
            aligned_outlines = self.align_outlines_parallel(outlines)
        else:
            aligned_outlines = self.align_outlines(outlines)
        # 使用对齐后的outlines进行分块
        chunks = self.sep_by_outline_with_outline_tree(
            content, aligned_outlines, org_chunk=chunk
        )

        return chunks

    def filter_outlines_parallel(self, raw_outlines):
        """
        过滤掉无效的标题，保留包含数字特征的标题。
        数字特征包括:
        1. 阿拉伯数字 (0-9)
        2. 中文数字 (一二三...百千万亿)
        3. 罗马数字 (I,II,III,IV...)
        4. 序号标记 (①,②,③...)
        5. 带数字的常见标记 (第x章、x.x、x)等
        """
        # 匹配纯数字和标点的无效标题
        invalid_pattern = r"""
                ^                      # 匹配开头
                [0-9一二三四五六七八九十零IIVXLCDM\-.\(\)\[\]\s]*  # 数字和标点
                $                      # 匹配结尾
            """

        # 匹配数字特征的模式
        number_pattern = r"""
                \d+                                          | # 阿拉伯数字
                [一二三四五六七八九十百千万亿]+              | # 中文数字
                [ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]+                          | # 中文罗马数字
                [IVXLCDMivxlcdm]+                           | # 英文罗马数字
                [①②③④⑤⑥⑦⑧⑨⑩]+                            | # 圈数字
                [⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽]+                            | # 括号数字
                第[一二三四五六七八九十百千万\d]+[章节篇部]    | # 第x章/节/篇/部
                [第]?[0-9一二三四五六七八九十百千万]+[条]     | # (第)x条
                \d+\.\d+                                     | # 数字层级(如1.1)
                [(]\d+[)]                                     # 括号数字
            """

        valid_outlines = []
        for title, level in raw_outlines:
            title = title.strip()
            # 过滤纯数字标题
            if re.fullmatch(invalid_pattern, title, re.VERBOSE):
                continue
            # 检查是否包含数字特征
            if not re.search(number_pattern, title, re.VERBOSE):
                continue
            valid_outlines.append((title, level))

        return valid_outlines

    def filter_outlines(self, raw_outlines):
        """
        过滤标题，只保留具有明确章节层级的标题。

        章节层级分为四级:
        1级(最高层): 篇、卷、部、编
        2级: 章
        3级: 节
        4级: 小节、款、项、目

        支持多种常见写法:
        - 带"第"字: 第一章、第1章
        - 不带"第"字: 一、1、(一)、(1)
        - 数字类型: 阿拉伯数字、中文数字、罗马数字
        """
        # 数字模式
        numbers = r"""
            (?:
                (?:[一二三四五六七八九十百千万]+)                  | # 中文数字
                (?:\d+)                                           | # 阿拉伯数字
                (?:[IVXLCDMivxlcdm]+)                            | # 罗马数字
                (?:①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳)                  | # 圈数字
                (?:\(\d+\))                                      | # (1)
                (?:\((?:[一二三四五六七八九十]+)\))                # (一)
            )
        """

        # 章节标识词
        level1_words = r"(?:篇|卷|部|编)"
        level2_words = r"(?:章)"
        level3_words = r"(?:节)"
        level4_words = r"(?:小节|款|项|目)"

        # 完整的章节匹配模式
        section_pattern = rf"""
            ^                                           # 匹配开头
            (?:
                (?:第\s*{numbers}\s*(?:{level1_words})) | # 第x篇/卷/部/编
                (?:第\s*{numbers}\s*(?:{level2_words})) | # 第x章
                (?:第\s*{numbers}\s*(?:{level3_words})) | # 第x节
                (?:第\s*{numbers}\s*(?:{level4_words})) | # 第x小节/款/项/目
                (?:{numbers}\s*[、.\s]\s*(?:{level1_words})) | # x、篇/卷/部/编
                (?:{numbers}\s*[、.\s]\s*(?:{level2_words})) | # x、章
                (?:{numbers}\s*[、.\s]\s*(?:{level3_words})) | # x、节
                (?:{numbers}\s*[、.\s]\s*(?:{level4_words}))   # x、小节/款/项/目
            )
            [\s\S]*                                     # 标题剩余部分
            $                                           # 匹配结尾
        """

        def determine_level(title: str) -> int:
            """根据标题内容确定层级"""
            if any(word in title for word in level1_words.strip("(?:)").split("|")):
                return 1
            elif any(word in title for word in level2_words.strip("(?:)").split("|")):
                return 2
            elif any(word in title for word in level3_words.strip("(?:)").split("|")):
                return 3
            elif any(word in title for word in level4_words.strip("(?:)").split("|")):
                return 4
            return 0  # 未匹配到任何层级

        valid_outlines = []
        for title, level in raw_outlines:
            title = title.strip()
            # 检查是否是有效的章节标题
            if re.match(section_pattern, title, re.VERBOSE):
                # 根据标题内容确定实际层级
                actual_level = determine_level(title)
                if actual_level > 0:  # 只添加成功确定层级的标题
                    valid_outlines.append((title, actual_level))

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
                id=generate_hash_id(f"{full_path}#{idx}"),
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
                id=generate_hash_id(f"{full_path}#{idx}"),
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
                id=generate_hash_id(f"{org_chunk.id}#{idx}"),
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
                id=generate_hash_id(f"{full_path}#{idx}"),
                name=full_path,
                content=chunk_content,
                **origin_properties,
                start=start,
                end=end,
            )
            chunks.append(chunk)
            father_stack.append((title, level))

        # 导出start end的chunk结果
        # dump_chunks_with_start_end(chunks, output_path="./start_end_chunk.json")

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
            sd_content = (start, end)
            outlines_with_content.append((title, t_content, sd_content, level))

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
            chunk_id = generate_hash_id(full_title)  # 使用完整title生成ID
            chunk = Chunk(
                id=chunk_id,
                name=full_title,  # 使用完整title
                content=node["content"],
                # 假设origin_properties是全局的或者在函数外部定义的，包含其他需要的属性
                **origin_properties,
                start=node["start"],
                end=node["end"],
            )
            chunks.append(chunk)

            # 递归为子节点生成chunk
            for child in node.get("children", []):
                generate_chunks(child, chunks, full_title)  # 将当前完整title传递给子节点

            return chunks

        chunks = []
        for node in catalog_tree:
            chunks.extend(generate_chunks(node))

        # 导出start end的chunk结果
        # dump_chunks_with_start_end(chunks, output_path="./start_end_chunk.json")

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

    def _invoke(self, input: Input, **kwargs) -> List[Chunk]:
        chunks = self.splitter_chunk(input, chunk_size=self.llm_max_tokens // 2)
        chunks = self.outline_chunk_batch(chunks)
        # chunks = self.splitter_chunk(chunks, chunk_size=self.chunk_size)
        # self.log(chunks)
        return chunks


if __name__ == "__main__":
    from kag.builder.component.splitter.length_splitter import LengthSplitter
    from kag.builder.component.reader.docx_reader import DocxReader
    from kag.builder.component.reader.txt_reader import TXTReader
    from kag.builder.component.reader.pdf_reader import PDFReader

    pdf_reader = PDFReader()
    docx_reader = DocxReader()
    txt_reader = TXTReader()
    length_splitter = LengthSplitter(split_length=5000)

    llm_config = {
        "api_key": "",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-max-latest",
        "type": "maas",
    }
    llm = LLMClient.from_config(llm_config)
    outline_splitter = OutlineSplitter(llm=llm)
    txt_path = os.path.join(
        os.path.dirname(__file__), "../../../../tests/builder/data/儿科学_short.txt"
    )
    docx_path = "/Users/zhangxinhong.zxh/Downloads/waikexue_short.docx"
    test_dir = "/Users/zhangxinhong.zxh/Downloads/1127_medkag_book"
    pdf_path = "/Users/zhangxinhong.zxh/Downloads/default.pdf"
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

    def process_txt(txt):
        chain = txt_reader >> outline_splitter
        chunks = chain.invoke(txt, max_workers=10)
        dump_chunks(chunks, output_path=txt.replace(".txt", ".json"))

    def process_file_without_chain(file):
        chunk = docx_reader.invoke(file)
        chunks = outline_splitter.invoke(chunk)
        dump_chunks(chunks, output_path=file.replace(".docx", ".json"))

    def process_txt_without_chain(txt):
        chunk = txt_reader.invoke(txt)
        chunks = outline_splitter.invoke(chunk)
        dump_chunks(chunks, output_path=txt.replace(".txt", ".json"))

    def process_pdf_without_chain(pdf):
        chunk = pdf_reader.invoke(pdf)
        chunks = outline_splitter.invoke(chunk)
        dump_chunks(chunks, output_path=pdf.replace(".pdf", ".json"))

    # with ThreadPoolExecutor(max_workers=10) as executor:
    #     futures = [executor.submit(process_file, file) for file in files]

    # for future in as_completed(futures):
    #     print(future.result())

    process_pdf_without_chain(pdf_path)
    a = 1
    # chunk = docx_reader.invoke(docx_path)
    # chunk = txt_reader.invoke(txt_path)
    # chunks = length_splitter.invoke(chunk)
    # chunks = outline_splitter.invoke(chunks)
    # print(chunks)
