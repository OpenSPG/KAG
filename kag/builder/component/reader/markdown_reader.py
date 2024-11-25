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
from typing import List, Type

from kag.builder.component.base import SourceReader
from kag.builder.model.chunk import Chunk
from kag.common.base.runnable import Output, Input


class MarkDownReader(SourceReader):
    """
    A class for reading MarkDown files, inheriting from `SourceReader`.
    Supports converting MarkDown data into a list of Chunk objects.

    Args:
        cut_depth (int): The depth of cutting, determining the level of detail in parsing. Default is 1.
    """

    ALL_LEVELS = [f"h{x}" for x in range(1, 7)]

    def __init__(self, cut_depth: int = 1):
        super().__init__()
        self.cut_depth = int(cut_depth)

    @property
    def input_types(self) -> Type[Input]:
        return str

    @property
    def output_types(self) -> Type[Output]:
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
                if tag.name == "table":
                    continue
                elif tag.name in self.ALL_LEVELS:
                    content.append(
                        f"{header}-{tag.text}" if len(header) > 0 else tag.text
                    )
                else:
                    content.append(tag.text)
        return "\n".join(content)

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
                        f"{parent_header}-{cur_header}"
                        if len(parent_header) > 0
                        else cur_header,
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
                if (
                    isinstance(sublevel_tags, tuple)
                    and sublevel_tags[1].name != "table"
                ):
                    cur_prefix.append(sublevel_tags[1].text)
                else:
                    break
            cur_prefix = "\n".join(cur_prefix)

            if len(cur_prefix) > 0:
                output.append(cur_prefix)
            for sublevel_tags in level_tags:
                if isinstance(sublevel_tags, list):
                    output.append(cur_prefix + "\n" + self.to_text(sublevel_tags))
            return output
        else:
            cur_prefix = []
            for sublevel_tags in level_tags:
                if (
                    isinstance(sublevel_tags, tuple)
                    and sublevel_tags[1].name != "table"
                ):
                    cur_prefix.append(sublevel_tags[1].text)
                else:
                    break
            cur_prefix = "\n".join(cur_prefix)
            if len(cur_prefix) > 0:
                output.append(cur_prefix)

            for sublevel_tags in level_tags:
                if isinstance(sublevel_tags, list):
                    output += self.cut(sublevel_tags, cur_level + 1, final_level)
            return output

    def solve_content(self, id: str, title: str, content: str) -> List[Output]:
        """
        Converts Markdown content into structured chunks.

        Args:
            id (str): An identifier for the content.
            title (str): The title of the content.
            content (str): The Markdown formatted content to be processed.

        Returns:
            List[Output]: A list of processed content chunks.
        """
        try:
            html_content = markdown.markdown(
                content, extensions=["markdown.extensions.tables"]
            )
            soup = BeautifulSoup(html_content, "html.parser")
        except Exception as e:
            raise RuntimeError(f"Error loading MarkDown file: {e}")

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
                id=Chunk.generate_hash_id(id),
                name=title,
                content=soup.text,
            )
            return [chunk]
        tags = [tag for tag in soup.children if isinstance(tag, Tag)]

        level_tags = self.parse_level_tags(tags, top_level)
        cutted = self.cut(level_tags, 0, self.cut_depth)

        chunks = []

        for idx, content in enumerate(cutted):
            chunks.append(
                Chunk(
                    id=Chunk.generate_hash_id(f"{id}#{idx}"),
                    name=f"{title}#{idx}",
                    content=content,
                )
            )
        return chunks

    def invoke(self, input: Input, **kwargs) -> List[Output]:
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
        return chunks
