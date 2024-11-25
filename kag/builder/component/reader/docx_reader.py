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
from typing import List, Type

from docx import Document

from kag.builder.model.chunk import Chunk
from kag.builder.component.base import SourceReader
from kag.common.base.runnable import Input, Output


class DocxReader(SourceReader):
    """
    A class for reading Docx files, inheriting from SourceReader.
    This class is specifically designed to extract text content from Docx files and generate Chunk objects based on the extracted content.
    """

    @property
    def input_types(self) -> Type[Input]:
        return str

    @property
    def output_types(self) -> Type[Output]:
        return Chunk

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
        return "\n".join(full_text)

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Processes the input Docx file, extracts its text content, and generates a Chunk object.

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

        try:
            doc = Document(input)
            content = self._extract_text_from_docx(doc)
        except OSError as e:
            raise IOError(f"Failed to read file: {input}") from e

        basename, _ = os.path.splitext(os.path.basename(input))
        chunk = Chunk(
            id=Chunk.generate_hash_id(input),
            name=basename,
            content=content,
        )
        return [chunk]
