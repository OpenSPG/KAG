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

from kag.builder.model.chunk import Chunk
from kag.interface.builder import SourceReaderABC
from knext.common.base.runnable import Input, Output


class TXTReader(SourceReaderABC):
    """
    A PDF reader class that inherits from SourceReader.
    """

    @property
    def input_types(self) -> Type[Input]:
        return str

    @property
    def output_types(self) -> Type[Output]:
        return Chunk

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        The main method for processing text reading. This method reads the content of the input (which can be a file path or text content) and converts it into a Chunk object.

        Args:
            input (Input): The input string, which can be the path to a text file or direct text content.
            **kwargs: Additional keyword arguments, currently unused but kept for potential future expansion.

        Returns:
            List[Output]: A list containing Chunk objects, each representing a piece of text read.

        Raises:
            ValueError: If the input is empty.
            IOError: If there is an issue reading the file specified by the input.
        """
        if not input:
            raise ValueError("Input cannot be empty")

        try:
            if os.path.exists(input):
                with open(input, "r", encoding='utf-8') as f:
                    content = f.read()
            else:
                content = input
        except OSError as e:
            raise IOError(f"Failed to read file: {input}") from e

        basename, _ = os.path.splitext(os.path.basename(input))
        chunk = Chunk(
            id=Chunk.generate_hash_id(input),
            name=basename,
            content=content,
        )
        return [chunk]
