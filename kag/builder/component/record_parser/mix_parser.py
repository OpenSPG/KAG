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
from kag.builder.component.record_parser.dict_parser import DictParser


@RecordParserABC.register("mix", as_default=True)
class MixParser(RecordParserABC):
    """
    A parser class that can handle multiple types of inputs by delegating to specific parsers.

    This class initializes with a mapping of file types to their respective parsers.
    It provides a method to invoke the appropriate parser based on the input type.

    """

    def __init__(
        self,
        txt_parser: TXTParser = None,
        pdf_parser: PDFParser = None,
        docx_parser: DocxParser = None,
        md_parser: MarkDownParser = None,
        dict_parser: DictParser = None,
    ):
        """
        Initializes the MixParser with a mapping of file types to their respective parsers.

        Args:
            txt_parser (TXTParser, optional): Parser for .txt files. Defaults to None.
            pdf_parser (PDFParser, optional): Parser for .pdf files. Defaults to None.
            docx_parser (DocxParser, optional): Parser for .docx files. Defaults to None.
            md_parser (MarkDownParser, optional): Parser for .md files. Defaults to None.
            dict_parser (DictParser, optional): Parser for dictionary inputs. Defaults to None.
        """
        self.parse_map = {
            "txt": txt_parser,
            "pdf": pdf_parser,
            "docx": docx_parser,
            "md": md_parser,
            "dict": dict_parser,
        }

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the appropriate parser based on the input type.

        Args:
            input (Input): The input to be parsed. This can be a file path or a dictionary.
            **kwargs: Additional keyword arguments to be passed to the parser.

        Returns:
            List[Output]: A list of parsed outputs.

        Raises:
            ValueError: If the input is empty.
            FileNotFoundError: If the input file does not exist.
            NotImplementedError: If the file suffix is not supported.
            KeyError: If the parser for the given file type is not correctly configured.
        """
        if not input:
            raise ValueError("Input cannot be empty")
        if isinstance(input, dict):
            parser_type = "dict"

        else:
            if os.path.exists(input):
                raise FileNotFoundError(f"File {input} not found.")

            file_suffix = input.split(".")[-1]
            if file_suffix not in self.parse_map:
                raise NotImplementedError(
                    f"File suffix {file_suffix} not supported yet."
                )
            parser_type = file_suffix

        parser = self.parser_map[parser_type]
        if parser is None:
            raise KeyError(f"{parser_type} parser not correctly configured.")
        return self.parse_map[file_suffix].invoke(input)
