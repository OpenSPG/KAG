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
from typing import List, Union

from docx import Document
from kag.interface import LLMClient
from kag.builder.model.chunk import Chunk
from kag.interface import ReaderABC
from kag.builder.prompt.outline_prompt import OutlinePrompt
from kag.common.conf import KAG_PROJECT_CONF
from kag.common.utils import generate_hash_id
from knext.common.base.runnable import Input, Output


def split_txt(content):
    from modelscope.outputs import OutputKeys
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks

    p = pipeline(
        task=Tasks.document_segmentation,
        model="damo/nlp_bert_document-segmentation_chinese-base",
    )

    result = p(documents=content)
    result = result[OutputKeys.TEXT]

    res = [r for r in result.split("\n\t") if len(r) > 0]

    return res


@ReaderABC.register("docx")
@ReaderABC.register("docx_reader")
class DocxReader(ReaderABC):
    """
    A class for reading Docx files into Chunk objects.

    This class inherits from ReaderABC and provides the functionality to process Docx files,
    extract their text content, and convert it into a list of Chunk objects.
    """

    def __init__(self, llm: LLMClient = None):
        """
        Initializes the DocxReader with an optional LLMClient instance.

        Args:
            llm (LLMClient): An optional LLMClient instance used for generating outlines. Defaults to None.
        """
        super().__init__()
        self.llm = llm
        self.prompt = OutlinePrompt(KAG_PROJECT_CONF.language)

    def outline_chunk(self, chunk: Union[Chunk, List[Chunk]], basename) -> List[Chunk]:
        """
        Generates outlines for the given chunk(s) and separates the content based on these outlines.

        Args:
            chunk (Union[Chunk, List[Chunk]]): A single Chunk object or a list of Chunk objects.
            basename: The base name used for generating chunk IDs and names.

        Returns:
            List[Chunk]: A list of Chunk objects separated by the generated outlines.
        """
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
        """
        Separates the content based on the provided outlines.

        Args:
            content (str): The content to be separated.
            outlines (List[str]): A list of outlines used to separate the content.
            basename: The base name used for generating chunk IDs and names.

        Returns:
            List[Chunk]: A list of Chunk objects separated by the provided outlines.
        """
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
                    pc[1] : position_check[idx + 1][1]
                    if idx + 1 < len(position_check)
                    else len(position_check)
                ],
            )
            chunks.append(chunk)
        return chunks

    @staticmethod
    def _extract_text_from_docx(doc: Document) -> str:
        """
        Extracts text from a Docx document.

        This method iterates through all paragraphs in the provided Docx document,
        appending each paragraph's text to a list, and then joins these texts into
        a single string separated by newline characters, effectively extracting the
        entire text content of the document.

        Args:
            doc (Document): A Document object representing the Docx file from which
                            text is to be extracted.

        Returns:
            str: A string containing all the text from the Docx document, with paragraphs
                 separated by newline characters.
        """
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return full_text

    def _get_title_from_text(self, text: str) -> str:
        """
        Extracts the title from the provided text.

        Args:
            text (str): The text from which to extract the title.

        Returns:
            str: The extracted title and the remaining text.
        """
        text = text.strip()
        title = text.split("\n")[0]
        text = "\n".join(text.split("\n"))
        return title, text

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Processes the input Docx file, extracts its text content, and generates Chunk objects.

        Args:
            input (Input): The file path of the Docx file to be processed.
            **kwargs: Additional keyword arguments, not used in the current implementation.

        Returns:
            List[Output]: A list containing a single Chunk object with the extracted text.

        Raises:
            ValueError: If the input is empty.
            IOError: If the file cannot be read or the text extraction fails.
        """

        if not input:
            raise ValueError("Input cannot be empty")

        chunks = []

        try:
            doc = Document(input)
            full_text = self._extract_text_from_docx(doc)
            content = "\n".join(full_text)
        except OSError as e:
            raise IOError(f"Failed to read file: {input}") from e

        basename, _ = os.path.splitext(os.path.basename(input))

        chunk = Chunk(
            id=generate_hash_id(input),
            name=basename,
            content=content,
            **{"documentId": basename, "documentName": basename},
        )
        chunks.append(chunk)

        return chunks
