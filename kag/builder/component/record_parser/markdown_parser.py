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

import os

import bs4.element
import markdown
from bs4 import BeautifulSoup, Tag
from typing import List

import logging
import re
import requests
import pandas as pd
from tenacity import stop_after_attempt, retry

from kag.interface import RecordParserABC
from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.builder.prompt.analyze_table_prompt import AnalyzeTablePrompt
from knext.common.base.runnable import Output, Input


logger = logging.getLogger(__name__)


@RecordParserABC.register("md")
class MarkDownParser(RecordParserABC):
    """
    A class for reading MarkDown files, inheriting from `SourceReader`.
    Supports converting MarkDown data into a list of Chunk objects.

    Args:
        cut_depth (int): The depth of cutting, determining the level of detail in parsing. Default is 1.
    """

    ALL_LEVELS = [f"h{x}" for x in range(1, 7)]
    TABLE_CHUCK_FLAG = "<<<table_chuck>>>"

    def __init__(self, cut_depth: int = 5, **kwargs):
        super().__init__(**kwargs)
        self.cut_depth = int(cut_depth)
        self.llm_module = self._init_llm()
        self.analyze_table_prompt = AnalyzeTablePrompt(language="zh")
        self.analyze_img_prompt = AnalyzeTablePrompt(language="zh")

    @property
    def input_types(self):
        return str

    @property
    def output_types(self):
        return Chunk

    def to_text(self, level_tags):
        """
        Converts parsed hierarchical tags into text content.

        Args:
            level_tags (list): Parsed tags organized by Markdown heading levels and other tags.

        Returns:
            str: Text content derived from the parsed tags.
        """
        content = []
        for item in level_tags:
            if isinstance(item, list):
                content.append(self.to_text(item))
            else:
                header, tag = item
                if not isinstance(tag, Tag):
                    continue
                elif tag.name in self.ALL_LEVELS:
                    content.append(
                        f"{header}-{tag.text}" if len(header) > 0 else tag.text
                    )
                else:
                    content.append(self.tag_to_text(tag))
        return "\n".join(content)

    def tag_to_text(self, tag: bs4.element.Tag):
        """
        将html tag转换为text
        如果是table，输出markdown，添加表格标记，方便后续构建Chunk
        :param tag:
        :return:
        """
        if tag.name == "table":
            try:
                html_table = str(tag)
                table_df = pd.read_html(html_table)[0]
                return f"{self.TABLE_CHUCK_FLAG}{table_df.to_markdown(index=False)}{self.TABLE_CHUCK_FLAG}"
            except:
                logging.warning("parse table tag to text error", exc_info=True)
        return tag.text

    @retry(stop=stop_after_attempt(5))
    def analyze_table(self, table, analyze_mathod="human"):
        if analyze_mathod == "llm":
            if self.llm_module is None:
                logging.INFO("llm_module is None, cannot use analyze_table")
                return table
            variables = {"table": table}
            response = self.llm_module.invoke(
                variables=variables,
                prompt_op=self.analyze_table_prompt,
                with_json_parse=False,
            )
            if response is None or response == "" or response == []:
                raise Exception("llm_module return None")
            return response
        else:
            from io import StringIO
            import pandas as pd

            try:
                df = pd.read_html(StringIO(table))[0]
            except Exception as e:
                logging.warning(f"analyze_table error: {e}")
                return table
            content = ""
            for index, row in df.iterrows():
                content += f"第{index+1}行的数据如下:"
                for col_name, value in row.items():
                    content += f"{col_name}的值为{value}，"
                content += "\n"
            return content

    @retry(stop=stop_after_attempt(5))
    def analyze_img(self, img_url):
        response = requests.get(img_url)
        response.raise_for_status()
        image_data = response.content
        return image_data

    def replace_table(self, content: str):
        pattern = r"<table[^>]*>([\s\S]*?)<\/table>"
        for match in re.finditer(pattern, content):
            table = match.group(0)
            table = self.analyze_table(table)
            content = content.replace(match.group(1), table)
        return content

    def replace_img(self, content: str):
        pattern = r"<img[^>]*src=[\"\']([^\"\']*)[\"\']"
        for match in re.finditer(pattern, content):
            img_url = match.group(1)
            img_msg = self.analyze_img(img_url)
            content = content.replace(match.group(0), img_msg)
        return content

    def extract_table(self, level_tags, header=""):
        """
        Extracts tables from the parsed hierarchical tags along with their headers.

        Args:
            level_tags (list): Parsed tags organized by Markdown heading levels and other tags.
            header (str): Current header text being processed.

        Returns:
            list: A list of tuples, each containing the table's header, context text, and the table tag.
        """
        tables = []
        for idx, item in enumerate(level_tags):
            if isinstance(item, list):
                tables += self.extract_table(item, header)
            else:
                tag = item[1]
                if not isinstance(tag, Tag):
                    continue
                if tag.name in self.ALL_LEVELS:
                    header = f"{header}-{tag.text}" if len(header) > 0 else tag.text

                if tag.name == "table":
                    if idx - 1 >= 0:
                        context = level_tags[idx - 1]
                        if isinstance(context, tuple):
                            tables.append((header, context[1].text, tag))
                    else:
                        tables.append((header, "", tag))
        return tables

    def parse_level_tags(
        self,
        level_tags: list,
        level: str,
        parent_header: str = "",
        cur_header: str = "",
    ):
        """
        Recursively parses level tags to organize them into a structured format.

        Args:
            level_tags (list): A list of tags to be parsed.
            level (str): The current level being processed.
            parent_header (str): The header of the parent tag.
            cur_header (str): The header of the current tag.

        Returns:
            list: A structured representation of the parsed tags.
        """
        if len(level_tags) == 0:
            return []
        output = []
        prefix_tags = []
        while len(level_tags) > 0:
            tag = level_tags[0]
            if tag.name in self.ALL_LEVELS:
                break
            else:
                prefix_tags.append((parent_header, level_tags.pop(0)))
        if len(prefix_tags) > 0:
            output.append(prefix_tags)

        cur = []
        while len(level_tags) > 0:
            tag = level_tags[0]
            if tag.name not in self.ALL_LEVELS:
                cur.append((parent_header, level_tags.pop(0)))
            else:

                if tag.name > level:
                    cur += self.parse_level_tags(
                        level_tags,
                        tag.name,
                        (
                            f"{parent_header}/{cur_header}"
                            if len(parent_header) > 0
                            else cur_header
                        ),
                        tag.name,
                    )
                elif tag.name == level:
                    if len(cur) > 0:
                        output.append(cur)
                    cur = [(parent_header, level_tags.pop(0))]
                    cur_header = tag.text
                else:
                    if len(cur) > 0:
                        output.append(cur)
                    return output
        if len(cur) > 0:
            output.append(cur)
        return output

    def cut(self, level_tags, cur_level, final_level):
        """
        Cuts the provided level tags into chunks based on the specified levels.

        Args:
            level_tags (list): A list of tags to be cut.
            cur_level (int): The current level in the hierarchy.
            final_level (int): The final level to which the tags should be cut.

        Returns:
            list: A list of cut chunks.
        """
        output = []
        if cur_level == final_level:
            cur_prefix = []
            for sublevel_tags in level_tags:
                if isinstance(sublevel_tags, tuple):
                    cur_prefix.append(
                        self.to_text(
                            [
                                sublevel_tags,
                            ]
                        )
                    )
                else:
                    break
            if cur_prefix:
                output.append("\n".join(cur_prefix))

            for sublevel_tags in level_tags:
                if isinstance(sublevel_tags, list):
                    output.append(self.to_text(sublevel_tags))
            return output
        else:
            cur_prefix = []
            for sublevel_tags in level_tags:
                if isinstance(sublevel_tags, tuple):
                    cur_prefix.append(sublevel_tags[1].text)
                else:
                    break
            if cur_prefix:
                output.append("\n".join(cur_prefix))

            for sublevel_tags in level_tags:
                if isinstance(sublevel_tags, list):
                    output += self.cut(sublevel_tags, cur_level + 1, final_level)
            return output

    def solve_content(
        self, id: str, title: str, content: str, **kwargs
    ) -> List[Output]:
        """
        Converts Markdown content into structured chunks.
        """
        html_content = markdown.markdown(
            content, extensions=["markdown.extensions.tables"]
        )
        soup = BeautifulSoup(html_content, "html.parser")
        if soup is None:
            raise ValueError("The MarkDown file appears to be empty or unreadable.")

        top_level = None
        for level in self.ALL_LEVELS:
            tmp = soup.find_all(level)
            if len(tmp) > 0:
                top_level = level
                break

        if top_level is None:
            chunk = Chunk(
                id=Chunk.generate_hash_id(str(id)),
                name=title,
                content=soup.text,
                ref=kwargs.get("ref", ""),
            )
            return [chunk]

        tags = [tag for tag in soup.children if isinstance(tag, Tag)]
        level_tags = self.parse_level_tags(tags, top_level)
        cutted = self.cut(level_tags, 0, self.cut_depth)

        # 获取每个chunk对应的完整标题路径
        chunk_titles = self._extract_chunk_titles(level_tags)

        # 只保留最后一级标题并确定层级
        chunk_levels = []
        final_titles = []
        for title_path in chunk_titles:
            final_title = title_path.split("/")[-1]
            final_titles.append(final_title)
            level = self._determine_title_level(final_title)
            chunk_levels.append(level)

        # 创建初始chunks
        initial_chunks = []
        if len(cutted) != len(chunk_titles):
            cutted = cutted[len(cutted) - len(chunk_titles) :]
        for idx, (content, full_title) in enumerate(zip(cutted, chunk_titles)):
            chunk = None
            chunk_name = f"{full_title}" if full_title else f"{title}#{idx}"

            if self.TABLE_CHUCK_FLAG in content:
                chunk = self.get_table_chuck(content, chunk_name, id, idx)
                chunk.ref = kwargs.get("ref", "")
                chunk.level = chunk_levels[idx]
            else:
                chunk = Chunk(
                    id=Chunk.generate_hash_id(f"{id}#{idx}"),
                    name=chunk_name,
                    content=content,
                    ref=kwargs.get("ref", ""),
                    level=chunk_levels[idx],
                )
            initial_chunks.append(chunk)

        # 构建chunk树
        chunk_tree = self.build_chunk_tree(initial_chunks)

        # 基于树结构合并chunks
        merged_chunks = self.merge_chunks_by_tree(chunk_tree, target_length=8000)
        return merged_chunks

    def count_tree_nodes(self, tree: dict) -> int:
        """
        计算树中的节点总数

        Args:
            tree: chunk树结构

        Returns:
            int: 节点总数
        """
        if not tree:
            return 0

        count = 1  # 当前节点
        for child in tree["children"]:
            count += self.count_tree_nodes(child)

        return count

    def build_chunk_tree(self, chunks: List[Chunk]) -> dict:
        """
        基于chunks的level构建树形结构

        Args:
            chunks: chunk列表

        Returns:
            dict: 树形结构，格式为:
            {
                'chunk': Chunk对象,
                'children': [子节点字典]
            }
        """
        root = {"chunk": None, "children": []}
        current_path = [root]

        for chunk in chunks:
            node = {"chunk": chunk, "children": []}

            # 找到当前chunk应该插入的位置
            while (
                len(current_path) > 1 and current_path[-1]["chunk"].level >= chunk.level
            ):
                current_path.pop()

            current_path[-1]["children"].append(node)
            current_path.append(node)

        # 如果需要打印节点数，可以在返回前添加：
        total_nodes = self.count_tree_nodes(root)
        logging.info(f"Built chunk tree with {total_nodes} nodes")

        return root

    def merge_chunks_by_tree(self, tree: dict, target_length: int) -> List[Chunk]:
        """
        基于树结构自适应合并chunks

        Args:
            tree: chunk树结构
            target_length: 目标chunk长度

        Returns:
            合并后的chunk列表
        """
        merged_chunks = []

        def merge_node(node: dict) -> Chunk:
            chunk = node["chunk"]
            if not node["children"]:
                return chunk

            # 先递归处理所有子节点
            child_chunks = []
            for child in node["children"]:
                # 表格类型的chunk不参与合并
                if child["chunk"].type == ChunkTypeEnum.Table:
                    merged_chunks.append(child["chunk"])
                    continue
                child_chunks.append(merge_node(child))

            # 计算当前节点及其子节点的总内容长度
            total_content = [chunk.content] if chunk else []
            total_content.extend(c.content for c in child_chunks)
            merged_content = "\n".join(filter(None, total_content))

            # 如果总长度小于目标长，合并所有内容
            if len(merged_content) <= target_length:
                if chunk:
                    chunk.content = merged_content
                    return chunk
                elif child_chunks:
                    child_chunks[0].content = merged_content
                    return child_chunks[0]

            # 否则，将子节点作为独立chunk保留
            merged_chunks.extend(child_chunks)
            return chunk

        root_result = merge_node(tree)
        if root_result:
            merged_chunks.append(root_result)

        return merged_chunks

    def _determine_title_level(self, title: str) -> int:
        """
        根据标题格式确定层级

        Args:
            title: 标题文本

        Returns:
            int: 标题层级(1-4)
        """
        title = title.strip()

        # 第X章 -> 1级
        if re.search(r"^第[一二三四五六七八九十\d]+章", title):
            return 1

        # 第X节 -> 2级
        if re.search(r"^第[一二三四五六七八九十\d]+节", title):
            return 2

        # 一、二、三... -> 3级
        if re.search(r"^[一二三四五六七八九十]+、", title):
            return 3

        # (一)、(二)、(三)... -> 4级
        if re.search(r"^\([一二三四五六七八九十]+\)", title):
            return 4

        # 1. 2. 3. -> 4级
        if re.search(r"^\d+\.", title):
            return 5

        # 其他情况默认为4级
        return 6

    def _extract_chunk_titles(self, level_tags):
        """
        提取每个chunk对应的完整标题路径

        Args:
            level_tags: 解析后的层级标签

        Returns:
            list: 每个chunk对应的完整标题路径列表
        """
        titles = []
        current_path = []

        def _traverse_tags(tags):
            for item in tags:
                if isinstance(item, list):
                    # 只在递归时处理，移除对 item[0] 的直接处理
                    _traverse_tags(item)
                elif isinstance(item, tuple):
                    header, tag = item
                    if isinstance(tag, Tag) and tag.name in self.ALL_LEVELS:
                        while len(current_path) >= int(tag.name[1]):
                            current_path.pop()
                        current_path.append(tag.text)
                        titles.append("/".join(current_path))

        _traverse_tags(level_tags)
        return titles

    def get_table_chuck(
        self, table_chunk_str: str, title: str, id: str, idx: int
    ) -> Chunk:
        """
        转换表格块
        :param table_chunk_str: 包含表格的文本块
        :return: 处理后的 Chunk 对象
        """
        table_chunk_str = table_chunk_str.replace("\\N", "")
        pattern = f"{self.TABLE_CHUCK_FLAG}(.*?){self.TABLE_CHUCK_FLAG}"
        matches = re.findall(pattern, table_chunk_str, re.DOTALL)
        if not matches or len(matches) <= 0:
            # 找不到表格信息，按照Text Chunk处理
            return Chunk(
                id=Chunk.generate_hash_id(f"{id}#{idx}"),
                name=f"{title}#{idx}",
                content=table_chunk_str,
            )
        table_markdown_str = matches[0]
        # 对markdown字符串中的反斜杠进行转义
        html_table_str = markdown.markdown(
            table_markdown_str, extensions=["markdown.extensions.tables"]
        )
        try:
            df = pd.read_html(html_table_str)[0]
        except Exception as e:
            logging.warning(f"get_table_chuck error: {e}")
            df = pd.DataFrame()

        # 确认是表格Chunk，去除内容中的TABLE_CHUCK_FLAG
        try:
            replaced_table_text = re.sub(
                pattern, f"\n{table_markdown_str}\n", table_chunk_str, flags=re.DOTALL
            )
        except Exception as e:
            logging.warning(f"get_table_chuck error: {e}")
            replaced_table_text = table_chunk_str
        return Chunk(
            id=Chunk.generate_hash_id(f"{id}#{idx}"),
            name=f"{title}#{idx}",
            content=replaced_table_text,
            type=ChunkTypeEnum.Table,
            csv_data=df.to_csv(index=False),
        )

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Processes a Markdown file and returns its content as structured chunks.

        Args:
            input (Input): The path to the Markdown file.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of processed content chunks.
        """
        file_path: str = input

        if not file_path.endswith(".md"):
            raise ValueError(f"Please provide a markdown file, got {file_path}")

        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"The file {file_path} does not exist.")

        with open(file_path, "r") as reader:
            content = reader.read()

        basename, _ = os.path.splitext(os.path.basename(file_path))

        chunks = self.solve_content(input, basename, content)
        length_500_list = []
        length_1000_list = []
        length_5000_list = []
        length_smal_list = []
        for chunk in chunks:
            if chunk.content is not None:
                if len(chunk.content) > 5000:
                    length_5000_list.append(chunk)
                elif len(chunk.content) > 1000:
                    length_1000_list.append(chunk)
                elif len(chunk.content) > 500:
                    length_500_list.append(chunk)
                elif len(chunk.content) <= 500:
                    length_smal_list.append(chunk)
        return chunks


@RecordParserABC.register("yuque")
class YuequeParser(MarkDownParser):
    """
    A class for parsing Yueque documents into Chunk objects.

    This class inherits from MarkDownParser and provides the functionality to process Yueque documents,
    extract their content, and convert it into a list of Chunk objects.
    """

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Processes the input Yueque document and converts it into a list of Chunk objects.

        Args:
            input (Input): The input string containing the Yueque token and URL.
            **kwargs: Additional keyword arguments, currently unused but kept for potential future expansion.

        Returns:
            List[Output]: A list of Chunk objects representing the parsed content.

        Raises:
            HTTPError: If the request to the Yueque URL fails.
        """
        token, url = input.split("@", 1)
        headers = {"X-Auth-Token": token}
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        data = response.json()["data"]
        id = data.get("id", "")
        title = data.get("title", "")
        content = data.get("body", "")

        chunks = self.solve_content(id, title, content)
        return chunks
