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
from io import StringIO
from tenacity import stop_after_attempt, retry

from kag.interface import ReaderABC
from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.interface import LLMClient
from kag.common.conf import KAG_PROJECT_CONF
from kag.common.utils import generate_hash_id
from kag.builder.prompt.analyze_table_prompt import AnalyzeTablePrompt
from knext.common.base.runnable import Output, Input


logger = logging.getLogger(__name__)


@ReaderABC.register("md")
class MarkDownReader(ReaderABC):
    """
    A class for reading Markdown content into Chunk objects.

    This class inherits from ReaderABC and provides the functionality to process Markdown content,
    extract its text and tables, and convert it into a list of Chunk objects.
    """

    ALL_LEVELS = [f"h{x}" for x in range(1, 7)]
    TABLE_CHUCK_FLAG = "<<<table_chuck>>>"

    def __init__(self, llm: LLMClient = None, cut_depth: int = 1):
        """
        Initializes the MarkDownReader with an optional LLMClient instance and cut depth.

        Args:
            llm (LLMClient): An optional LLMClient instance used for analyzing tables. Defaults to None.
            cut_depth (int): The depth at which to cut the content for parsing. Defaults to 1.
        """
        super().__init__()
        self.llm = llm
        self.cut_depth = cut_depth
        self.analyze_table_prompt = AnalyzeTablePrompt(
            language=KAG_PROJECT_CONF.language
        )

    def to_text(self, level_tags):
        """
        Converts the given level tags into a text format.

        Args:
            level_tags: A list of level tags to be converted into text.

        Returns:
            str: The text representation of the level tags.
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
        Converts a BeautifulSoup Tag object into text.

        Args:
            tag (bs4.element.Tag): The BeautifulSoup Tag object to be converted.

        Returns:
            str: The text representation of the Tag object.
        """
        if tag.name == "table":
            try:
                html_table = str(tag)
                table_df = pd.read_html(StringIO(html_table))[0]
                return f"{self.TABLE_CHUCK_FLAG}{table_df.to_markdown(index=False)}{self.TABLE_CHUCK_FLAG}"
            except Exception as e:
                logger.warning(f"parse table tag to text error: {e}", exc_info=True)
        return tag.text

    @retry(stop=stop_after_attempt(5))
    def analyze_table(self, table, analyze_mathod="human"):
        """
        Analyzes the given table content using the specified method.

        Args:
            table: The table content to be analyzed.
            analyze_mathod (str): The method to use for analyzing the table. Defaults to "human".

        Returns:
            str: The analyzed table content.

        Raises:
            Exception: If the LLM module returns None.
        """
        if analyze_mathod == "llm":
            if self.llm is None:
                logger.INFO("llm_module is None, cannot use analyze_table")
                return table
            variables = {"table": table}
            response = self.llm.invoke(
                variables=variables,
                prompt_op=self.analyze_table_prompt,
                with_json_parse=False,
            )
            if response is None or response == "" or response == []:
                raise Exception("llm_module return None")
            return response
        else:
            import pandas as pd

            try:
                df = pd.read_html(StringIO(table))[0]
            except Exception as e:
                logger.warning(f"analyze_table error: {e}")
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
        """
        Analyzes the given image URL.

        Args:
            img_url (str): The URL of the image to be analyzed.

        Returns:
            str: The analyzed image content.

        Raises:
            HTTPError: If the request to the image URL fails.
        """
        response = requests.get(img_url)
        response.raise_for_status()

        pass

    def replace_table(self, content: str):
        """
        Replaces table tags in the content with their analyzed text representation.

        Args:
            content (str): The content containing table tags to be replaced.

        Returns:
            str: The content with table tags replaced by their analyzed text.
        """
        pattern = r"<table[^>]*>([\s\S]*?)<\/table>"
        for match in re.finditer(pattern, content):
            table = match.group(0)
            table = self.analyze_table(table)
            content = content.replace(match.group(1), table)
        return content

    def replace_img(self, content: str):
        """
        Replaces image tags in the content with their analyzed text representation.

        Args:
            content (str): The content containing image tags to be replaced.

        Returns:
            str: The content with image tags replaced by their analyzed text.
        """
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
                if isinstance(sublevel_tags, tuple):
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

    def solve_content(
        self, id: str, title: str, content: str, **kwargs
    ) -> List[Output]:
        """
        Converts Markdown content into structured chunks.

        Args:
            id (str): An identifier for the content.
            title (str): The title of the content.
            content (str): The Markdown formatted content to be processed.

        Returns:
            List[Output]: A list of processed content chunks.
        """
        html_content = markdown.markdown(
            content, extensions=["markdown.extensions.tables"]
        )
        # html_content = self.replace_table(html_content)
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
                id=generate_hash_id(str(id)),
                name=title,
                content=soup.text,
                ref=kwargs.get("ref", ""),
            )
            return [chunk]
        tags = [tag for tag in soup.children if isinstance(tag, Tag)]

        level_tags = self.parse_level_tags(tags, top_level)
        cutted = self.cut(level_tags, 0, self.cut_depth)

        chunks = []

        for idx, content in enumerate(cutted):
            chunk = None
            if self.TABLE_CHUCK_FLAG in content:
                chunk = self.get_table_chuck(content, title, id, idx)
                chunk.ref = kwargs.get("ref", "")
            else:
                chunk = Chunk(
                    id=generate_hash_id(f"{id}#{idx}"),
                    name=f"{title}#{idx}",
                    content=content,
                    ref=kwargs.get("ref", ""),
                )
            chunks.append(chunk)
        return chunks

    def get_table_chuck(
        self, table_chunk_str: str, title: str, id: str, idx: int
    ) -> Chunk:
        """
        Converts a table chunk string into a Chunk object.

        This method processes a table chunk string, extracts the table content, and converts it into a Chunk object.
        If the table chunk string does not contain a valid table, it is treated as a text chunk.

        Args:
            table_chunk_str (str): The table chunk string to be processed.
            title (str): The title of the chunk.
            id (str): The ID of the chunk.
            idx (int): The index of the chunk.

        Returns:
            Chunk: A Chunk object representing the table chunk.
        """
        table_chunk_str = table_chunk_str.replace("\\N", "")
        pattern = f"{self.TABLE_CHUCK_FLAG}(.*){self.TABLE_CHUCK_FLAG}"
        matches = re.findall(pattern, table_chunk_str, re.DOTALL)
        if not matches or len(matches) <= 0:
            # 找不到表格信息，按照Text Chunk处理
            return Chunk(
                id=generate_hash_id(f"{id}#{idx}"),
                name=f"{title}#{idx}",
                content=table_chunk_str,
            )
        table_markdown_str = matches[0]
        html_table_str = markdown.markdown(
            table_markdown_str, extensions=["markdown.extensions.tables"]
        )
        try:
            df = pd.read_html(StringIO(html_table_str))[0]
        except Exception as e:
            logger.warning(f"get_table_chuck error: {e}")
            df = pd.DataFrame()

        # 确认是表格Chunk，去除内容中的TABLE_CHUCK_FLAG
        replaced_table_text = re.sub(
            pattern, f"\n{table_markdown_str}\n", table_chunk_str, flags=re.DOTALL
        )
        return Chunk(
            id=generate_hash_id(f"{id}#{idx}"),
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
        return chunks


@ReaderABC.register("yuque")
class YuequeReader(MarkDownReader):
    """
    A class for reading Yueque documents into Chunk objects.

    This class inherits from MarkDownReader and provides the functionality to process Yueque documents,
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
    a = 1
