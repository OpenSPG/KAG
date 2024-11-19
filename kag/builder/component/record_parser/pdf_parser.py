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
from typing import List, Sequence, Union

import pdfminer.layout  # noqa


from kag.builder.model.chunk import Chunk
from kag.interface import RecordParserABC

from kag.builder.prompt.outline_prompt import OutlinePrompt
from kag.interface import LLMClient
from kag.common.conf import KAG_PROJECT_CONF
from knext.common.base.runnable import Input, Output
from pdfminer.high_level import extract_text
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
import pdfminer  # noqa


import logging

logger = logging.getLogger(__name__)


@RecordParserABC.register("pdf")
class PDFFileParser(RecordParserABC):
    """
    A PDF reader class that inherits from RecordParserABC.
    """

    def __init__(self, llm: LLMClient = None, split_level: int = 3):

        self.split_level = split_level
        # self.split_using_outline = split_using_outline
        # self.outline_flag = True
        self.llm = llm
        self.prompt = OutlinePrompt(KAG_PROJECT_CONF.language)

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
                id=Chunk.generate_hash_id(f"{basename}#{pc[0]}"),
                name=f"{basename}#{pc[0]}",
                content=content[
                    pc[1] : position_check[idx + 1][1]
                    if idx + 1 < len(position_check)
                    else len(position_check)
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

    def invoke(self, input: Input, **kwargs) -> Sequence[Output]:
        """
        Processes a PDF file, splitting or extracting content based on configuration.

        Args:
            input (str): The path to the PDF file.
            **kwargs: Additional keyword arguments, such as `clean_list`.

        Returns:
            Sequence[Output]: A sequence of processed outputs.

        Raises:
            ValueError: If the file is not a PDF file or the content is empty/unreadable.
            FileNotFoundError: If the file does not exist.
        """
        if not input.endswith(".pdf"):
            raise ValueError(f"Please provide a pdf file, got {input}")

        if not os.path.isfile(input):
            raise FileNotFoundError(f"The file {input} does not exist.")

        self.fd = open(input, "rb")
        self.parser = PDFParser(self.fd)
        self.document = PDFDocument(self.parser)
        chunks = []
        basename, _ = os.path.splitext(os.path.basename(input))

        # get outline
        try:
            outlines = self.document.get_outlines()
            outline_flag = True
        except Exception as e:
            logger.warning(f"failed to get outline, info: {e}")
            outline_flag = False

        if not outline_flag:

            with open(input, "rb") as file:
                for idx, page_layout in enumerate(extract_pages(file)):
                    content = ""
                    for element in page_layout:
                        if hasattr(element, "get_text"):
                            content = content + element.get_text()
                    chunk = Chunk(
                        id=Chunk.generate_hash_id(f"{basename}#{idx}"),
                        name=f"{basename}#{idx}",
                        content=content,
                    )
                    chunks.append(chunk)
            if self.llm is not None:
                try:
                    outline_chunks = self.outline_chunk(chunks, basename)
                except Exception as e:
                    raise RuntimeError(f"Error loading PDF file: {e}")
                if len(outline_chunks) > 0:
                    chunks = outline_chunks
        else:
            split_words = []

            for item in outlines:
                level, title, dest, a, se = item
                split_words.append(title.strip().replace(" ", ""))
            # save the outline position in content
            try:
                text = extract_text(input)

            except Exception as e:
                raise RuntimeError(f"Error loading PDF file: {e}")

            cleaned_pages = [
                self._process_single_page(x, "", False, False) for x in text
            ]
            sentences = []
            for cleaned_page in cleaned_pages:
                sentences += cleaned_page

            content = "".join(sentences)
            positions = [(input, 0)]
            for split_word in split_words:
                pattern = re.compile(split_word)
                for i, match in enumerate(re.finditer(pattern, content)):
                    if i == 1:
                        start, end = match.span()
                        positions.append((split_word, start))

            for idx, position in enumerate(positions):
                chunk = Chunk(
                    id=Chunk.generate_hash_id(f"{basename}#{position[0]}"),
                    name=f"{basename}#{position[0]}",
                    content=content[
                        position[1] : positions[idx + 1][1]
                        if idx + 1 < len(positions)
                        else None
                    ],
                )
                chunks.append(chunk)

        return chunks
