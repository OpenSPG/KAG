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

import markdown
from bs4 import BeautifulSoup, Tag
from typing import List, Dict

import logging
import re
import requests
import pandas as pd

from kag.interface import RecordParserABC
from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.builder.prompt.analyze_table_prompt import AnalyzeTablePrompt
from knext.common.base.runnable import Output, Input
from kag.common.utils import generate_hash_id


logger = logging.getLogger(__name__)


class MarkdownNode:
    def __init__(self, title: str, level: int, content: str = ""):
        self.title = title
        self.level = level
        self.content = content
        self.children: List[MarkdownNode] = []
        self.tables: List[Dict] = []  # 存储表格数据


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

    def __init__(self, cut_depth: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.cut_depth = int(cut_depth)
        self.llm_module = kwargs.get("llm_module", None)
        self.analyze_table_prompt = AnalyzeTablePrompt(language="zh")
        self.analyze_img_prompt = AnalyzeTablePrompt(language="zh")

    @property
    def input_types(self):
        return str

    @property
    def output_types(self):
        return Chunk

    def solve_content(
        self, id: str, title: str, content: str, **kwargs
    ) -> List[Output]:
        # 将Markdown转换为HTML
        html = markdown.markdown(content, extensions=["tables"])
        soup = BeautifulSoup(html, "html.parser")

        # 初始化根节点
        root = MarkdownNode("root", 0)
        stack = [root]

        # 遍历所有元素
        for element in soup.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6", "p", "table"]
        ):
            if element.name.startswith("h"):
                # 获取标题级别
                level = int(element.name[1])
                title_text = element.get_text().strip()

                # 创建新节点
                new_node = MarkdownNode(title_text, level)

                # 找到合适的父节点
                while stack and stack[-1].level >= level:
                    stack.pop()

                if stack:
                    stack[-1].children.append(new_node)
                stack.append(new_node)

            elif element.name == "table":
                # 处理表格
                table_data = []
                headers = []

                # 获取表头
                if element.find("thead"):
                    for th in element.find("thead").find_all("th"):
                        headers.append(th.get_text().strip())

                # 获取表格内容
                if element.find("tbody"):
                    for row in element.find("tbody").find_all("tr"):
                        row_data = {}
                        for i, td in enumerate(row.find_all("td")):
                            if i < len(headers):
                                row_data[headers[i]] = td.get_text().strip()
                        table_data.append(row_data)

                # 将表格添加到当前节点和所有父节点
                for node in stack:
                    node.tables.append({"headers": headers, "data": table_data})

            elif element.name == "p":
                # 处理段落文本，添加到当前节点和所有父节点
                text = element.get_text().strip() + "\n"
                for node in stack:
                    if node.title != "root":  # 不添加到根节点
                        node.content += text

        # 将树状结构转换为输出格式
        outputs = self._convert_to_outputs(root, id)
        return outputs

    def _convert_to_outputs(
        self,
        node: MarkdownNode,
        id: str,
        parent_id: str = None,
        parent_titles: List[str] = None,
        parent_contents: List[str] = None,
    ) -> List[Output]:
        outputs = []
        if parent_titles is None:
            parent_titles = []
        if parent_contents is None:
            parent_contents = []

        current_titles = parent_titles + ([node.title] if node.title != "root" else [])
        current_contents = parent_contents + (
            [node.content] if node.content and node.title != "root" else []
        )

        # 如果当前节点级别等于目标级别，收集所有内容
        if node.level == self.cut_depth:
            # 处理目标级别的节点
            full_title = " / ".join(current_titles)

            # 收集所有内容（包括父级内容）
            all_content = current_contents.copy()

            # 收集所有子节点的内容
            def collect_children_content(n: MarkdownNode):
                content = [n.content] if n.content else []
                for child in n.children:
                    content.extend(collect_children_content(child))
                return content

            for child in node.children:
                all_content.extend(collect_children_content(child))

            current_output = Chunk(
                id=f"{id}_{len(outputs)}",
                parent_id=parent_id,
                name=full_title,
                content="\n".join(filter(None, all_content)),
            )

            # 收集表格数据
            all_tables = []
            if node.tables:
                all_tables.extend(node.tables)

            def collect_tables(n: MarkdownNode):
                tables = []
                if n.tables:
                    tables.extend(n.tables)
                for child in n.children:
                    tables.extend(collect_tables(child))
                return tables

            for child in node.children:
                all_tables.extend(collect_tables(child))

            if all_tables:
                current_output.metadata = {"tables": all_tables}

            outputs.append(current_output)

        # 如果当前节点级别小于目标级别，继续向下遍历
        elif node.level < self.cut_depth:
            # 检查是否有任何子树包含目标级别的节点
            has_target_level = False
            for child in node.children:
                child_outputs = self._convert_to_outputs(
                    child, id, parent_id, current_titles, current_contents
                )
                if child_outputs:
                    has_target_level = True
                    outputs.extend(child_outputs)

            # 如果没有找到目标级别的节点，且当前节点不是根节点，则输出当前节点
            if not has_target_level and node.title != "root":
                full_title = " / ".join(current_titles)

                # 收集所有内容（包括父级内容）
                all_content = current_contents.copy()

                # 收集所有子节点的内容
                def collect_children_content(n: MarkdownNode):
                    content = [n.content] if n.content else []
                    for child in n.children:
                        content.extend(collect_children_content(child))
                    return content

                for child in node.children:
                    all_content.extend(collect_children_content(child))

                current_output = Chunk(
                    id=f"{id}_{len(outputs)}",
                    parent_id=parent_id,
                    name=full_title,
                    content="\n".join(filter(None, all_content)),
                )

                # 收集表格数据
                all_tables = []
                if node.tables:
                    all_tables.extend(node.tables)

                def collect_tables(n: MarkdownNode):
                    tables = []
                    if n.tables:
                        tables.extend(n.tables)
                    for child in n.children:
                        tables.extend(collect_tables(child))
                    return tables

                for child in node.children:
                    all_tables.extend(collect_tables(child))

                if all_tables:
                    current_output.metadata = {"tables": all_tables}

                outputs.append(current_output)

        return outputs

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


if __name__ == "__main__":
    markdown_parser = MarkDownParser()
    res = markdown_parser._invoke("/Users/zhangxinhong.zxh/Downloads/Noah文档中心-sdk.md")
    from kag.builder.model.chunk import dump_chunks

    dump_chunks(res)
    a = 1
