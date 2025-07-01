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
import urllib.parse  # Import for URL decoding
from typing import List

from kag.builder.model.chunk import Chunk
from kag.interface import ReaderABC
from kag.common.utils import generate_hash_id
from knext.common.base.runnable import Input, Output

import logging

logger = logging.getLogger(__name__)


@ReaderABC.register("txt")
@ReaderABC.register("txt_reader")
class TXTReader(ReaderABC):
    """
    A class for parsing text files or text content into Chunk objects.

    This class inherits from ReaderABC and provides the functionality to read text content,
    whether it is from a file or directly provided as a string, and convert it into a list of Chunk objects.
    """

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        The main method for processing text reading. This method reads the content of the input
        (which can be a file path or text content) and converts it into chunks.

        Optionally performs URL decoding on the input path if it's treated as a path.

        Args:
            input (Input): The input string, which can be the path to a text file or direct text content.
            **kwargs:
                perform_url_decode (bool, optional): Whether to perform URL (percent) decoding
                    on the input string if it's treated as a path. Defaults to True.

        Returns:
            List[Output]: A list containing Chunk objects, each representing a piece of text read.

        Raises:
            ValueError: If the input is empty.
            IOError: If there is an issue reading the file specified by the input.
        """
        if not input:
            raise ValueError("Input cannot be empty")

        # --- Get the flag from kwargs, default to True ---
        perform_url_decode = kwargs.get("perform_url_decode", False)
        # -----------------------------------------------

        # --- Added URL decoding logic (conditionally) ---
        path_str = input
        if not isinstance(path_str, str):
            try:
                path_str = str(input)
            except Exception as e:
                raise TypeError(
                    f"Input cannot be converted to string: {input}. Error: {e}"
                )

        original_input_repr = repr(path_str)

        # --- Conditionally perform URL decoding ---
        if perform_url_decode:
            try:
                # Attempt to decode percent-encoding (URL encoding)
                decoded_path = urllib.parse.unquote(path_str)
                if decoded_path != path_str:
                    print(
                        f"DEBUG: Successfully URL-decoded input: {original_input_repr} -> '{decoded_path}'"
                    )
                path_str = decoded_path
            except Exception as e:
                print(
                    f"WARN: Unexpected error during URL decoding attempt for {original_input_repr}: {e}"
                )
                path_str = original_input_repr
        else:
            print(f"DEBUG: URL decoding skipped for input: {original_input_repr}")
        # --- End of conditional decoding ---

        # The rest of the code uses path_str, which is now potentially decoded
        print(f"DEBUG: Processing file path: '{path_str}'")

        is_file = os.path.isfile(path_str)

        if is_file:
            try:
                with open(path_str, "r", encoding="utf-8") as f:
                    file_content = f.read()
                basename, _ = os.path.splitext(os.path.basename(path_str))
                logger.info(f"Read content from file: {path_str}")
            except OSError as e:
                raise IOError(
                    f"Failed to read file: '{path_str}' (Original input was: {original_input_repr})"
                ) from e
            except Exception as e:
                raise RuntimeError(
                    f"An unexpected error occurred while reading file '{path_str}': {e}"
                )
        else:
            file_content = path_str
            basename = "direct_content"
            logger.info("Input is not a file path, treating as direct content.")

        chunk = Chunk(
            id=generate_hash_id(path_str),
            name=urllib.parse.unquote(basename),
            content=file_content,
        )
        return [chunk]


if __name__ == "__main__":
    reader = TXTReader()
    reader.invoke("ckpt/file_scanner/%E5%91%A8%E6%9D%B0%E4%BC%A6.txt")
