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
import re
from typing import List, Union, Dict, Tuple

import pdfminer.layout  # noqa


from kag.builder.model.chunk import Chunk
from kag.builder.model.sub_graph import Edge, Node, SubGraph
from kag.interface import ReaderABC

from kag.builder.prompt.outline_prompt import OutlinePrompt
from kag.interface import LLMClient
from kag.common.utils import generate_hash_id
from knext.common.base.runnable import Input, Output
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
import pdfminer  # noqa
import PyPDF2

from kag.builder.component.splitter.length_splitter import LengthSplitter

import logging

logger = logging.getLogger(__name__)


@ReaderABC.register("pdf")
@ReaderABC.register("pdf_reader")
class PDFReader(ReaderABC):
    """
    A class for reading PDF files into a list of text chunks, inheriting from `ReaderABC`.

    This class is responsible for parsing PDF files and converting them into a list of Chunk objects.
    It inherits from `ReaderABC` and overrides the necessary methods to handle PDF-specific operations.
    """

    def __init__(
        self,
        cut_depth: int = 3,
        outline_flag: bool = True,
        is_ocr: bool = False,
        llm: LLMClient = None,
        length_splitter: LengthSplitter = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.cut_depth = cut_depth
        self.outline_flag = outline_flag
        self.is_ocr = is_ocr
        self.llm = llm
        self.length_splitter = length_splitter
        self.prompt = OutlinePrompt(self.language)

    @property
    def input_types(self):
        return str

    @property
    def output_types(self):
        return Chunk

    def _get_full_outlines(self):
        outlines = self.pdf_reader.outline
        level_outlines = []

        def _extract_outline_page_numbers(outlines, level=0):
            for outline in outlines:
                if isinstance(outline, list):
                    _extract_outline_page_numbers(outline, level + 1)
                else:
                    title = outline.title
                    page_number = self.pdf_reader.get_destination_page_number(outline)
                    level_outlines.append((title, level, page_number, 0))

        _extract_outline_page_numbers(outlines)
        for idx, outline in enumerate(level_outlines):
            level_outlines[idx] = (
                outline[0],
                outline[1],
                outline[2],
                level_outlines[idx + 1][2] if idx + 1 < len(level_outlines) else -1,
            )
        return level_outlines

    def extract_content_from_outline(
        self, page_contents, level_outlines
    ) -> List[Chunk]:
        total_content = "".join(page_contents)

        def get_content_start(outline, page_contents):
            page_start = outline[2]
            page_end = outline[3]

            previous_pages_length = sum(
                len(content) for content in page_contents[:page_start]
            )

            find_content = "".join(
                page_contents[page_start : page_end + 1 if page_end != -1 else None]
            )

            # 标准化标题中的特殊字符
            def normalize_text(text):
                # 将破折号"—"转换为中文数字"一"
                text = text.replace("—", "一")
                # 可以添加其他中英文标点的统一转换
                text = re.sub(r"［", "[", text)
                text = re.sub(r"］", "]", text)
                text = re.sub(r"（", "(", text)
                text = re.sub(r"）", ")", text)
                return text

            outline = (normalize_text(outline[0]), outline[1], outline[2], outline[3])

            def fuzzy_search(pattern, text, threshold=0.90):
                from difflib import SequenceMatcher

                pattern_len = len(pattern)
                for i in range(len(text) - pattern_len + 1):
                    substring = text[i : i + pattern_len]
                    similarity = SequenceMatcher(None, pattern, substring).ratio()
                    if similarity >= threshold:
                        return i
                return -1

            # 先尝试使用原始标题进行模糊匹配
            title_with_spaces = outline[0].strip()
            fuzzy_match_pos = fuzzy_search(title_with_spaces, find_content)
            if fuzzy_match_pos != -1:
                return previous_pages_length + fuzzy_match_pos

            # 如果没找到，尝试使用去除所有空格的标题
            title_no_spaces = title_with_spaces.replace(" ", "")
            find_content_no_spaces = find_content.replace(" ", "")
            fuzzy_match_pos = fuzzy_search(title_no_spaces, find_content_no_spaces)

            if fuzzy_match_pos != -1:
                # 计算原始文本中的实际位置
                original_pos = 0
                no_spaces_pos = 0
                while no_spaces_pos < fuzzy_match_pos:
                    if find_content[original_pos] != " ":
                        no_spaces_pos += 1
                    original_pos += 1
                return previous_pages_length + original_pos

            # 在扩展范围内进行模糊匹配
            extended_content = "".join(
                page_contents[
                    max(0, page_start - 1) : page_end if page_end != -1 else None
                ]
            )

            fuzzy_match_pos = fuzzy_search(title_with_spaces, extended_content)
            if fuzzy_match_pos != -1:
                extended_previous_length = sum(
                    len(content) for content in page_contents[: max(0, page_start - 1)]
                )
                return extended_previous_length + fuzzy_match_pos

            # 最后尝试不带空格的扩展内容
            extended_content_no_spaces = extended_content.replace(" ", "")
            fuzzy_match_pos = fuzzy_search(title_no_spaces, extended_content_no_spaces)
            if fuzzy_match_pos != -1:
                original_pos = 0
                no_spaces_pos = 0
                while no_spaces_pos < fuzzy_match_pos:
                    if extended_content[original_pos] != " ":
                        no_spaces_pos += 1
                    original_pos += 1

                extended_previous_length = sum(
                    len(content) for content in page_contents[: max(0, page_start - 1)]
                )
                return extended_previous_length + original_pos

            return -1

        final_content = []
        for idx, outline in enumerate(level_outlines):
            start = get_content_start(outline, page_contents)
            next_start = (
                get_content_start(level_outlines[idx + 1], page_contents)
                if idx + 1 < len(level_outlines)
                else -1
            )
            if start >= 0 and next_start >= 0:
                content = total_content[start:next_start]
                final_content.append(
                    (outline[0], outline[1], start, next_start, content)
                )
            elif start >= 0 and next_start < 0 and idx + 1 == len(level_outlines):
                content = total_content[start:]
                final_content.append((outline[0], outline[1], start, -1, content))
        return final_content

    def convert_finel_content_to_chunks(
        self, final_content
    ) -> Tuple[List[Chunk], SubGraph]:
        def create_chunk(title, content, basename):
            chunk = Chunk(
                id=generate_hash_id(f"{basename}#{title}"),
                name=f"{basename}#{title}",
                content=content,
                sub_chunks=[],
            )
            # Apply length splitter if configured and content is too long
            if self.length_splitter:
                split_chunks = self.length_splitter.slide_window_chunk(
                    chunk,
                    self.length_splitter.split_length,
                    self.length_splitter.window_length,
                )
                for split_chunk in split_chunks:
                    split_chunk.parent_id = chunk.id
                return split_chunks
            return [chunk]

        level_map = {}
        chunks = []
        nodes = []
        edges = []
        node_map = {}  # Track created nodes by ID
        chunk_nodes = {}  # Track chunk nodes by their IDs

        def add_bidirectional_edge(
            from_node: Node, to_node: Node, label: str, properties: Dict = None
        ):
            """Helper function to add bidirectional edges"""
            if properties is None:
                properties = {}

            # Forward edge
            edges.append(
                Edge(
                    _id="",
                    from_node=from_node,
                    to_node=to_node,
                    label=label,
                    properties=properties.copy(),
                )
            )

            # Backward edge
            reverse_label = {
                "hasChild": "hasParent",
                "hasContent": "belongsToTitle",
            }.get(label, f"reverse_{label}")

            edges.append(
                Edge(
                    _id="",
                    from_node=to_node,
                    to_node=from_node,
                    label=reverse_label,
                    properties=properties.copy(),
                )
            )

        # Create root node using filename
        basename = os.path.splitext(os.path.basename(self.fd.name))[0]
        root_node_id = f"node_root_{basename}"
        root_node = Node(
            _id=root_node_id, name=basename, label="Title", properties={"level": "0"}
        )
        nodes.append(root_node)
        node_map[root_node_id] = root_node

        for title, level, start, end, content in final_content:
            created_chunks = create_chunk(title, content, basename)
            chunks.extend(created_chunks)

            # Create title node
            title_node_id = f"node_{hash(title)}"
            if title_node_id not in node_map:
                title_node = Node(
                    _id=title_node_id,
                    name=title,
                    label="Title",
                    properties={"level": str(level)},
                )
                nodes.append(title_node)
                node_map[title_node_id] = title_node
            else:
                title_node = node_map[title_node_id]

            # Create chunk nodes and connect them to title
            for chunk in created_chunks:
                chunk_node = Node(
                    _id=chunk.id,
                    name=chunk.name,
                    label="Chunk",
                    properties={
                        "content": chunk.content,
                    },
                )
                nodes.append(chunk_node)
                chunk_nodes[chunk.id] = chunk_node

                # Create bidirectional edges between title and chunk
                add_bidirectional_edge(title_node, chunk_node, "hasContent")

            # Connect to parent based on level
            if level == 0:
                level_map[0] = chunks[-1]  # Use last chunk as level marker
                # Connect level 0 titles to root
                add_bidirectional_edge(
                    root_node, title_node, "hasChild", {"level": "1"}
                )
            else:
                # Try to find parent in previous levels
                parent_found = False
                parent_level = level - 1
                while parent_level >= 0:
                    if parent_level in level_map:
                        for chunk in created_chunks:
                            level_map[parent_level].sub_chunks.append(chunk)
                        # Add title hierarchy relationship
                        parent_chunk = level_map[parent_level]
                        parent_title_node = node_map[
                            f"node_{hash(parent_chunk.name.split('#')[1])}"
                        ]
                        add_bidirectional_edge(
                            parent_title_node,
                            title_node,
                            "hasChild",
                            {"level": str(level)},
                        )
                        parent_found = True
                        break
                    parent_level -= 1

                # If no parent found, connect to root
                if not parent_found:
                    add_bidirectional_edge(
                        root_node, title_node, "hasChild", {"level": str(level)}
                    )

                level_map[level] = chunks[-1]  # Use last chunk as level marker

        subgraph = SubGraph(nodes=nodes, edges=edges)
        return chunks, subgraph

    def outline_chunk(self, chunk: Union[Chunk, List[Chunk]], basename) -> List[Chunk]:
        if isinstance(chunk, Chunk):
            chunk = [chunk]
        outlines = []
        for c in chunk:
            outline = self.llm.invoke({"input": c.content}, self.prompt)
            outlines.extend(outline)
        content = "\n".join([c.content for c in chunk])
        chunks = self.sep_by_outline(content, outlines, basename)
        return chunks

    def sep_by_outline(self, content, outlines, basename):
        position_check = []
        for outline in outlines:
            start = content.find(outline)
            position_check.append((outline, start))
        chunks = []
        for idx, pc in enumerate(position_check):
            chunk = Chunk(
                id=generate_hash_id(f"{basename}#{pc[0]}"),
                name=f"{basename}#{pc[0]}",
                content=content[
                    pc[1] : (
                        position_check[idx + 1][1]
                        if idx + 1 < len(position_check)
                        else len(position_check)
                    )
                ],
            )
            chunks.append(chunk)
        return chunks

    @staticmethod
    def _process_single_page(
        page: str,
        watermark: str,
        remove_header: bool = False,
        remove_footnote: bool = False,
        remove_lists: List[str] = None,
    ) -> list:
        """
        Processes a single page of text, removing headers, footnotes, watermarks, and specified lists.

        Args:
            page (str): The text content of a single page.
            watermark (str): The watermark text to be removed.
            remove_header (bool): Whether to remove the header. Default is False.
            remove_footnote (bool): Whether to remove the footnote. Default is False.
            remove_lists (List[str]): A list of strings to be removed. Default is None.

        Returns:
            list: A list of processed text lines.
        """
        lines = page.split("\n")
        if remove_header and len(lines) > 0:
            lines = lines[1:]
        if remove_footnote and len(lines) > 0:
            lines = lines[:-1]

        cleaned = [line.strip().replace(watermark, "") for line in lines]

        if remove_lists is None:
            return cleaned
        for s in remove_lists:
            cleaned = [line.strip().replace(s, "") for line in cleaned]

        return cleaned

    @staticmethod
    def _extract_text_from_page(page_layout: LTPage) -> str:
        """
        Extracts text from a given page layout.

        Args:
            page_layout (LTPage): The layout of the page containing text elements.

        Returns:
            str: The extracted text.
        """
        text = ""
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                text += element.get_text()
        return text

    def _invoke(self, input: Input, **kwargs) -> Tuple[List[Output], SubGraph]:
        """
        Processes a PDF file and returns its content as structured chunks and a graph representation.

        Args:
            input (Input): The path to the PDF file.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple[List[Output], SubGraph]: A tuple containing:
                - A list of processed content chunks
                - A SubGraph representation of the document structure
        """
        if not input.endswith(".pdf"):
            raise ValueError(f"Please provide a pdf file, got {input}")

        if not os.path.isfile(input):
            raise FileNotFoundError(f"The file {input} does not exist.")

        self.fd = None
        try:
            self.fd = open(input, "rb")
            self.pdf_reader = PyPDF2.PdfReader(self.fd)
            self.level_outlines = self._get_full_outlines()
            self.parser = PDFParser(self.fd)
            self.document = PDFDocument(self.parser)
            chunks = []
            basename, _ = os.path.splitext(os.path.basename(input))

            # get outline
            try:
                outlines = self.document.get_outlines()  # noqa
            except Exception as e:
                logger.warning(f"loading PDF file: {e}")
                self.outline_flag = False

            if not self.outline_flag:
                with open(input, "rb") as file:
                    for idx, page_layout in enumerate(extract_pages(file)):
                        content = ""
                        for element in page_layout:
                            if hasattr(element, "get_text"):
                                content = content + element.get_text()
                        chunk = Chunk(
                            id=generate_hash_id(f"{basename}#{idx}"),
                            name=f"{basename}#{idx}",
                            content=content,
                        )
                        chunks.append(chunk)

            else:
                split_words = []  # noqa

                page_contents = []

                with open(input, "rb") as file:
                    for idx, page_layout in enumerate(extract_pages(file)):
                        content = ""
                        for element in page_layout:
                            if hasattr(element, "get_text"):
                                content = content + element.get_text()
                        content = content.replace("\n", "")
                        page_contents.append(content)

                # 使用正则表达式移除所有空白字符（包括空格、制表符、换行符等）
                page_contents = [
                    re.sub(r"\s+", "", content) for content in page_contents
                ]
                page_contents = [
                    re.sub(r"[\s\u200b\u200c\u200d\ufeff]+", "", content)
                    for content in page_contents
                ]
                page_contents = ["".join(content.split()) for content in page_contents]

                final_content = self.extract_content_from_outline(
                    page_contents, self.level_outlines
                )
                chunks, subgraph = self.convert_finel_content_to_chunks(final_content)

            return chunks

        except Exception as e:
            raise RuntimeError(f"Error loading PDF file: {e}")
        finally:
            if self.fd:
                self.fd.close()


if __name__ == "__main__":
    pdf_reader = ReaderABC.from_config(
        {
            "type": "pdf_reader",
            "length_splitter": {
                "type": "length_splitter",
                "split_length": 50,
                "window_length": 10,
                "language": "zh",
            },
        }
    )
    pdf_path = os.path.join(
        os.path.dirname(__file__), "../../../../tests/unit/builder/data/aiwen.pdf"
    )
    # pdf_path = "/Users/zhangxinhong.zxh/Downloads/toaz.info-5dsm-5-pr_56e68a629dc4fe62699960dd5afbe362.pdf"
    chunk = pdf_reader.invoke(pdf_path)
    a = 1
