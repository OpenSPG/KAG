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
import io

import markdown
from bs4 import BeautifulSoup, Tag

import logging
import re
import requests
import pandas as pd
from typing import List, Dict, Tuple

from kag.builder.component.writer.kg_writer import KGWriter
from kag.common.utils import generate_hash_id
from kag.interface import ReaderABC
from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.interface import LLMClient
from kag.builder.prompt.analyze_table_prompt import AnalyzeTablePrompt
from knext.common.base.runnable import Output, Input
from kag.builder.model.sub_graph import SubGraph, Node, Edge


logger = logging.getLogger(__name__)


class MarkdownNode:
    def __init__(self, title: str, level: int, content: str = ""):
        self.title = title
        self.level = level
        self.content = content
        self.children: List[MarkdownNode] = []
        self.tables: List[Dict] = []  # 存储表格数据


@ReaderABC.register("md")
@ReaderABC.register("md_reader")
class MarkDownReader(ReaderABC):
    """
    A class for reading MarkDown files, inheriting from `SourceReader`.
    Supports converting MarkDown data into a list of Chunk objects.

    Args:
        cut_depth (int): The depth of cutting, determining the level of detail in parsing. Default is 1.
    """

    ALL_LEVELS = [f"h{x}" for x in range(1, 7)]
    TABLE_CHUCK_FLAG = "<<<table_chuck>>>"

    def __init__(self, cut_depth: int = 3, llm: LLMClient = None, kg_writer: KGWriter = None, **kwargs):
        super().__init__(**kwargs)
        self.cut_depth = int(cut_depth)
        self.llm = llm
        self.kg_writer = kg_writer
        self.analyze_table_prompt = AnalyzeTablePrompt(language="zh")
        self.analyze_img_prompt = AnalyzeTablePrompt(language="zh")

    @property
    def input_types(self):
        return str

    @property
    def output_types(self):
        return Tuple[List[Chunk], Dict[MarkdownNode, Chunk], MarkdownNode, Tuple[SubGraph, dict]]

    def solve_content(
        self, id: str, title: str, content: str, **kwargs
    ) -> Tuple[List[Output], Dict[MarkdownNode, Output], MarkdownNode, Tuple[SubGraph, dict]]:
        # Convert Markdown to HTML with additional extensions for lists
        html = markdown.markdown(
            content, extensions=["tables", "nl2br", "sane_lists", "fenced_code"]
        )
        soup = BeautifulSoup(html, "html.parser")

        def is_in_code_block(element):
            """Check if an element is inside a code block"""
            parent = element.parent
            while parent:
                if parent.name in ["pre", "code"]:
                    return True
                parent = parent.parent
            return False

        def process_text_with_links(element):
            """Process text containing links, preserving original markdown format"""
            result = []
            current_text = ""

            for child in element.children:
                if isinstance(child, Tag):
                    if child.name == "a":
                        # If there's previous text, add it first
                        if current_text:
                            result.append(current_text.strip())
                            current_text = ""

                        # Rebuild markdown format link
                        link_text = child.get_text().strip()
                        href = child.get("href", "")
                        title = child.get("title", "")

                        if title:
                            result.append(f'[{link_text}]({href} "{title}")')
                        else:
                            result.append(f"[{link_text}]({href})")
                    else:
                        current_text += child.get_text()
                else:
                    current_text += str(child)

            if current_text:
                result.append(current_text.strip())

            return " ".join(result)

        # Initialize root node
        root = MarkdownNode("root", 0)
        stack = [root]
        current_content = []

        # Traverse all elements
        all_elements = soup.find_all(
            [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "p",
                "table",
                "ul",
                "ol",
                "li",
                "pre",
                "code",
            ]
        )
        for element in all_elements:
            if element.name.startswith("h") and not is_in_code_block(element):
                # Only process headers that are not in code blocks
                # Handle title logic
                if current_content and stack[-1].title != "root":
                    stack[-1].content = "\n".join(current_content)
                current_content = []

                level = int(element.name[1])
                title_text = process_text_with_links(element)  # Process links in title
                new_node = MarkdownNode(title_text, level)

                while stack and stack[-1].level >= level:
                    stack.pop()

                if stack:
                    stack[-1].children.append(new_node)
                stack.append(new_node)

            elif element.name in ["code"]:
                # Preserve code blocks as is
                text = element.get_text()
                if text:
                    current_content.append(text)

            elif element.name in ["ul", "ol"]:
                continue

            elif element.name == "li":
                text = process_text_with_links(element)  # Process links in list items
                if text:
                    if element.find_parent("ol"):
                        index = len(element.find_previous_siblings("li")) + 1
                        current_content.append(f"{index}. {text}")
                    else:
                        current_content.append(f"* {text}")

            elif element.name == "table":
                # Process table directly using pandas
                table_html = str(element)
                try:
                    # Add converters parameter to handle escaped strings
                    df = pd.read_html(
                        io.StringIO(table_html), 
                        header=0,
                        converters={i: str for i in range(20)}  # Convert all columns to string
                    )[0]
                    
                    # Clean up the data by removing escaped quotes
                    df = df.applymap(lambda x: str(x).strip('"\\"') if isinstance(x, str) else x)
                    
                    # Replace 'Unnamed' headers with empty string
                    df.columns = ['' if 'Unnamed' in str(col) else str(col).strip('"\\"') for col in df.columns]
                    headers = df.columns.tolist()

                    # Capture table context (text before and after the table)
                    table_context = {
                        "before_text": "",
                        "after_text": ""
                    }
                    
                    # Get text before table
                    prev_texts = []
                    prev_element = element.find_previous_sibling()
                    while prev_element:
                        if prev_element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                            break
                        if prev_element.name == "p":
                            prev_texts.insert(0, process_text_with_links(prev_element))
                        prev_element = prev_element.find_previous_sibling()
                    table_context["before_text"] = "\n".join(prev_texts) if prev_texts else ""

                    # Get text after table
                    next_texts = []
                    next_element = element.find_next_sibling()
                    while next_element:
                        if next_element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                            break
                        if next_element.name == "p":
                            next_texts.append(process_text_with_links(next_element))
                        next_element = next_element.find_next_sibling()
                    table_context["after_text"] = "\n".join(next_texts) if next_texts else ""

                    # Add table to current node with context
                    if stack[-1].title != "root":
                        stack[-1].tables.append({
                            "headers": headers, 
                            "data": df,
                            "context": table_context
                        })

                except Exception as e:
                    logger.warning(f"Failed to parse table: {e}")
                    continue

            elif element.name == "p":
                text = process_text_with_links(element)  # Process links in paragraphs
                if text:
                    if not text.startswith("* ") and not re.match(r"^\d+\. ", text):
                        current_content.append(text)

        # Process content of the last node
        if current_content and stack[-1].title != "root":
            stack[-1].content = "\n".join(current_content)

        outputs, node_chunk_map = self._convert_to_outputs(root, id)
        
        # Convert to SubGraph using the function from markdown_to_graph
        from kag.builder.component.reader.markdown_to_graph import convert_to_subgraph
        subgraph_and_stats = convert_to_subgraph(root, outputs, node_chunk_map)

        if self.kg_writer:
            self.kg_writer.invoke(subgraph_and_stats[0])
        
        return outputs

    def _convert_to_outputs(
        self,
        node: MarkdownNode,
        id: str,
        parent_id: str = None,
        parent_titles: List[str] = None,
        parent_contents: List[str] = None,
    ) -> Tuple[List[Output], Dict[MarkdownNode, Output]]:
        def convert_table_to_markdown(headers, data):
            """Convert table data to markdown format"""
            if not headers or data.empty:
                return ""
            data:pd.DataFrame = data
            data = data.fillna("")
            data = data.astype(str)
            return "\n" + data.to_markdown(index=False) + "\n"

        def collect_tables(n: MarkdownNode):
            """Collect tables from node and its children"""
            tables = []
            table_md = []
            if n.tables:
                for table in n.tables:
                    tables.append(table)
                    table_md.append(
                        convert_table_to_markdown(table["headers"], table["data"])
                    )
            for child in n.children:
                child_tables, child_table_md = collect_tables(child)
                tables.extend(child_tables)
                table_md.extend(child_table_md)
            return tables, table_md

        def collect_children_content(n: MarkdownNode):
            """Collect content from node and its children"""
            content = []
            if n.content:
                content.append(n.content)
            # Process child nodes recursively
            for child in n.children:
                content.extend(collect_children_content(child))
            return content

        outputs = []
        node_chunk_map = {}  # Track mapping between nodes and their chunks
        if parent_titles is None:
            parent_titles = []
        if parent_contents is None:
            parent_contents = []

        current_titles = parent_titles + ([node.title] if node.title != "root" else [])

        # If current node level equals target level, create output
        if node.level >= self.cut_depth:
            full_title = " / ".join(current_titles)

            # Store parent content separately
            parent_content = "\n".join(filter(None, parent_contents)) if parent_contents else None

            # Current node's own content and child content
            current_content = [node.content] if node.content else []
            for child in node.children:
                child_content = collect_children_content(child)
                current_content.extend(child_content)

            current_output = Chunk(
                id=f"{generate_hash_id(full_title)}",
                parent_id=parent_id,
                name=full_title,
                content="\n".join(filter(None, current_content)),
                parent_content=parent_content,
            )
            outputs.append(current_output)
            node_chunk_map[node] = current_output  # Add mapping

            # Create separate chunks for tables
            all_tables = []
            if node.tables:
                for i, table in enumerate(node.tables):
                    table_content = convert_table_to_markdown(table["headers"], table["data"])
                    table_chunk = Chunk(
                        id=f"{generate_hash_id(f'{full_title} / Table {i+1}')}",
                        parent_id=current_output.id,
                        name=f"{full_title} / Table {i+1}",
                        content=table_content,
                        type=ChunkTypeEnum.Table,
                        metadata={
                            "table_data": table,
                            "before_text": table.get("context", {}).get("before_text", ""),
                            "after_text": table.get("context", {}).get("after_text", "")
                        }
                    )
                    outputs.append(table_chunk)
                    all_tables.append(table)

            for child in node.children:
                child_tables, _ = collect_tables(child)
                for i, table in enumerate(child_tables, start=len(all_tables)):
                    table_content = convert_table_to_markdown(table["headers"], table["data"])
                    table_chunk = Chunk(
                        id=f"{generate_hash_id(f'{full_title} / Table {i+1}')}",
                        parent_id=current_output.id,
                        name=f"{full_title} / Table {i+1}",
                        content=table_content,
                        type=ChunkTypeEnum.Table,
                        metadata={
                            "table_data": table,
                            "before_text": table.get("context", {}).get("before_text", ""),
                            "after_text": table.get("context", {}).get("after_text", "")
                        }
                    )
                    outputs.append(table_chunk)
                    all_tables.append(table)

        # If current node level is less than target level, continue traversing
        elif node.level < self.cut_depth:
            # Check if any subtree contains target level nodes
            has_target_level = False
            current_contents = parent_contents + ([node.content] if node.content else [])

            for child in node.children:
                child_outputs, child_map = self._convert_to_outputs(
                    child, id, parent_id, current_titles, current_contents
                )
                if child_outputs:
                    has_target_level = True
                    outputs.extend(child_outputs)
                    node_chunk_map.update(child_map)  # Merge child mappings

            # If no target level nodes found and current node is not root, output current node
            if not has_target_level and node.title != "root":
                full_title = " / ".join(current_titles)
                
                # Store parent content separately
                parent_content = "\n".join(filter(None, parent_contents)) if parent_contents else None

                # Current node's own content and child content
                current_content = [node.content] if node.content else []
                for child in node.children:
                    child_content = collect_children_content(child)
                    current_content.extend(child_content)

                current_output = Chunk(
                    id=f"{generate_hash_id(full_title)}",
                    parent_id=parent_id,
                    name=full_title,
                    content="\n".join(filter(None, current_content)),
                    parent_content=parent_content,
                )
                outputs.append(current_output)
                node_chunk_map[node] = current_output  # Add mapping

                # Create separate chunks for tables
                all_tables = []
                if node.tables:
                    for i, table in enumerate(node.tables):
                        table_content = convert_table_to_markdown(table["headers"], table["data"])
                        table_chunk = Chunk(
                            id=f"{generate_hash_id(f'{full_title} / Table {i+1}')}",
                            parent_id=current_output.id,
                            name=f"{full_title} / Table {i+1}",
                            content=table_content,
                            type=ChunkTypeEnum.Table,
                            metadata={
                                "table_data": table,
                                "before_text": table.get("context", {}).get("before_text", ""),
                                "after_text": table.get("context", {}).get("after_text", "")
                            }
                        )
                        outputs.append(table_chunk)
                        all_tables.append(table)

                for child in node.children:
                    child_tables, _ = collect_tables(child)
                    for i, table in enumerate(child_tables, start=len(all_tables)):
                        table_content = convert_table_to_markdown(table["headers"], table["data"])
                        table_chunk = Chunk(
                            id=f"{generate_hash_id(f'{full_title} / Table {i+1}')}",
                            parent_id=current_output.id,
                            name=f"{full_title} / Table {i+1}",
                            content=table_content,
                            type=ChunkTypeEnum.Table,
                            metadata={
                                "table_data": table,
                                "before_text": table.get("context", {}).get("before_text", ""),
                                "after_text": table.get("context", {}).get("after_text", "")
                            }
                        )
                        outputs.append(table_chunk)
                        all_tables.append(table)

        return outputs, node_chunk_map

    def _invoke(self, input: Input, **kwargs) -> Tuple[List[Output], Dict[MarkdownNode, Output], MarkdownNode, Tuple[SubGraph, dict]]:
        """
        Processes a Markdown file and returns its content as structured chunks.

        Args:
            input (Input): The path to the Markdown file.
            **kwargs: Additional keyword arguments.

        Returns:
            tuple[List[Output], Dict[MarkdownNode, Output], MarkdownNode, Tuple[SubGraph, dict]]: A tuple containing:
                - A list of processed content chunks
                - A dictionary mapping MarkdownNode objects to their corresponding Chunk objects
                - The root MarkdownNode of the document tree
                - A SubGraph representation of the document structure
        """
        file_path: str = input

        if not file_path.endswith(".md"):
            raise ValueError(f"Please provide a markdown file, got {file_path}")

        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"The file {file_path} does not exist.")

        with open(file_path, "r") as reader:
            content = reader.read()

        basename, _ = os.path.splitext(os.path.basename(file_path))

        chunks, node_chunk_map, root, (subgraph, stats) = self.solve_content(input, basename, content)
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


@ReaderABC.register("yuque")
@ReaderABC.register("yuque_reader")
class YuequeReader(MarkDownReader):
    """
    A class for parsing Yueque documents into Chunk objects.

    This class inherits from MarkDownParser and provides the functionality to process Yueque documents,
    extract their content, and convert it into a list of Chunk objects.
    """

    def _invoke(self, input: Input, **kwargs) -> Tuple[List[Output], Dict[MarkdownNode, Output], MarkdownNode, Tuple[SubGraph, dict]]:
        """
        Processes the input Yueque document and converts it into a list of Chunk objects.

        Args:
            input (Input): The input string containing the Yueque token and URL.
            **kwargs: Additional keyword arguments, currently unused but kept for potential future expansion.

        Returns:
            tuple[List[Output], Dict[MarkdownNode, Output], MarkdownNode, Tuple[SubGraph, dict]]: A tuple containing:
                - A list of Chunk objects representing the parsed content
                - A dictionary mapping MarkdownNode objects to their corresponding Chunk objects
                - The root MarkdownNode of the document tree
                - A SubGraph representation of the document structure

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

        chunks, node_chunk_map, root, (subgraph, stats) = self.solve_content(id, title, content)
        return chunks

if __name__ == "__main__":
    from kag.builder.component.reader.markdown_to_graph import visualize_graph

    reader = ReaderABC.from_config({"type": "md", "cut_depth": 2, "kg_writer": {"type": "kg", "project_id": 1}})
    file_path = "/Users/zhangxinhong.zxh/Downloads/人卫书籍-15本/20240820_02.外科学（第8版）_4020.md"
    chunks = reader.invoke(file_path)
    assert len(chunks) > 0
    print(chunks)