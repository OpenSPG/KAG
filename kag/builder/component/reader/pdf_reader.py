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
from typing import List, Sequence, Type

from langchain_community.document_loaders import PyPDFLoader

from kag.builder.model.chunk import Chunk
from kag.builder.component.base import SourceReader
from kag.common.base.runnable import Input, Output

from pdfminer.high_level import extract_text
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTPage


class PDFReader(SourceReader):
    """
    A PDF reader class that inherits from SourceReader.

    Attributes:
        if_split (bool): Whether to split the content by pages. Default is False.
        use_pypdf (bool): Whether to use PyPDF2 for processing PDF files. Default is True.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.if_split = kwargs.get("if_split", False)
        self.use_pypdf = kwargs.get("use_pypdf", True)

    @property
    def input_types(self) -> Type[Input]:
        return str

    @property
    def output_types(self) -> Type[Output]:
        return Chunk

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

    def invoke(self, input: str, **kwargs) -> Sequence[Output]:
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

        if self.use_pypdf:
            try:
                loader = PyPDFLoader(input)
                pages = loader.load_and_split()

            except Exception as e:
                raise RuntimeError(f"Error loading PDF file: {e}")

            clean_list = kwargs.get("clean_list", None)
            cleaned_pages = [
                self._process_single_page(x.page_content, "", False, False, clean_list)
                for x in pages
            ]
            sentences = []
            for cleaned_page in cleaned_pages:
                sentences += cleaned_page
            basename, _ = os.path.splitext(os.path.basename(input))

            content = "".join(sentences)
            if not content:
                raise ValueError("The PDF file appears to be empty or unreadable.")

            chunk = Chunk(
                id=Chunk.generate_hash_id(input),
                name=basename,
                content=content,
            )
            return [chunk]
        else:
            if not self.if_split:
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
                basename, _ = os.path.splitext(os.path.basename(input))

                content = "".join(sentences)
                if not content:
                    raise ValueError("The PDF file appears to be empty or unreadable.")

                chunk = Chunk(
                    id=Chunk.generate_hash_id(input),
                    name=basename,
                    content=content,
                )
                return [chunk]
            else:
                chunks = []
                with open(input, "rb") as file:
                    for idx, page_layout in enumerate(extract_pages(file)):
                        basename, _ = os.path.splitext(os.path.basename(input))
                        content = ""
                        for element in page_layout:
                            if isinstance(element, LTPage):
                                content = content + self._extract_text_from_page(
                                    element
                                )
                        chunk = Chunk(
                            id=Chunk.generate_hash_id(f"{input}#{idx}"),
                            name=f"{basename}#{idx}",
                            content=content,
                        )
                        chunks.append(chunk)
                return chunks
