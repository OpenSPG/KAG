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
from typing import List

from kag.interface import RecordParserABC
from knext.common.base.runnable import Input, Output
from kag.builder.component.record_parser.txt_parser import TXTParser
from kag.builder.component.record_parser.pdf_parser import PDFParser
from kag.builder.component.record_parser.docx_parser import DocxParser
from kag.builder.component.record_parser.markdown_parser import MarkDownParser


@RecordParserABC.register("file")
class FileParser(RecordParserABC):
    """
    A class for parsing files of different formats using specific parsers.

    This class inherits from `RecordParserABC` and provides a mapping of file
    suffixes to their respective parsers. It allows for invoking the appropriate
    parser based on the file type.
    """

    def __init__(
        self,
        txt_parser: TXTParser = None,
        pdf_parser: PDFParser = None,
        docx_parser: DocxParser = None,
        md_parser: MarkDownParser = None,
    ):
        """
        Initializes a new instance of the FileParser class.

        Args:
            txt_parser (TXTParser, optional): The parser for .txt files. Defaults to None.
            pdf_parser (PDFParser, optional): The parser for .pdf files. Defaults to None.
            docx_parser (DocxParser, optional): The parser for .docx files. Defaults to None.
            md_parser (MarkDownParser, optional): The parser for .md files. Defaults to None.
        """
        self.parse_map = {
            "txt": txt_parser,
            "pdf": pdf_parser,
            "docx": docx_parser,
            "md": md_parser,
        }

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the appropriate parser based on the file type.

        Args:
            input (Input): The input file path or object.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of parsed outputs.

        Raises:
            ValueError: If the input is empty.
            FileNotFoundError: If the file does not exist.
            NotImplementedError: If the file suffix is not supported.
            KeyError: If the file parser for the given suffix is not configured.
        """
        if not input:
            raise ValueError("Input cannot be empty")

        if os.path.exists(input):
            raise FileNotFoundError(f"File {input} not found.")

        file_suffix = input.split(".")[-1]
        if file_suffix not in self.parse_map:
            raise NotImplementedError(f"File suffix {file_suffix} not supported yet.")
        if self.parse_map[file_suffix] is None:
            raise KeyError(f"{file_suffix} file parser not configured.")
        return self.parse_map[file_suffix].invoke(input)
