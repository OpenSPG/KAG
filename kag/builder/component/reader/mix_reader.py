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

from kag.interface import ReaderABC
from knext.common.base.runnable import Input, Output
from kag.builder.component.reader.txt_reader import TXTReader
from kag.builder.component.reader.pdf_reader import PDFReader
from kag.builder.component.reader.docx_reader import DocxReader
from kag.builder.component.reader.markdown_reader import MarkDownReader
from kag.builder.component.reader.dict_reader import DictReader


@ReaderABC.register("mix", as_default=True)
@ReaderABC.register("mix_reader")
class MixReader(ReaderABC):
    """
    A reader class that can handle multiple types of inputs by delegating to specific readers.

    This class initializes with a mapping of file types to their respective readers.
    It provides a method to invoke the appropriate reader based on the input type.

    """

    def __init__(
        self,
        txt_reader: TXTReader = None,
        pdf_reader: PDFReader = None,
        docx_reader: DocxReader = None,
        md_reader: MarkDownReader = None,
        dict_reader: DictReader = None,
        **kwargs,
    ):
        """
        Initializes the MixReader with a mapping of file types to their respective readers.

        Args:
            txt_reader (TXTReader, optional): Reader for .txt files. Defaults to None.
            pdf_reader (PDFReader, optional): Reader for .pdf files. Defaults to None.
            docx_reader (DocxReader, optional): Reader for .docx files. Defaults to None.
            md_reader (MarkDownReader, optional): Reader for .md files. Defaults to None.
            dict_reader (DictReader, optional): Reader for dictionary inputs. Defaults to None.
        """
        super().__init__(**kwargs)
        self.reader_map = {
            "txt": txt_reader,
            "pdf": pdf_reader,
            "docx": docx_reader,
            "md": md_reader,
            "dict": dict_reader,
        }

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the appropriate reader based on the input type.

        Args:
            input (Input): The input to be parsed. This can be a file path or a dictionary.
            **kwargs: Additional keyword arguments to be passed to the reader.

        Returns:
            List[Output]: A list of parsed outputs.

        Raises:
            ValueError: If the input is empty.
            FileNotFoundError: If the input file does not exist.
            NotImplementedError: If the file suffix is not supported.
            KeyError: If the reader for the given file type is not correctly configured.
        """
        if not input:
            raise ValueError("Input cannot be empty")
        if isinstance(input, dict):
            reader_type = "dict"

        else:
            if not os.path.exists(input):
                raise FileNotFoundError(f"File {input} not found.")

            file_suffix = input.split(".")[-1]
            if file_suffix not in self.reader_map:
                raise NotImplementedError(
                    f"File suffix {file_suffix} not supported yet."
                )
            reader_type = file_suffix

        reader = self.reader_map[reader_type]
        if reader is None:
            raise KeyError(f"{reader_type} reader not correctly configured.")
        return reader._invoke(input)
