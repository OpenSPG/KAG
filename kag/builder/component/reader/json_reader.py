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

import json
import os
from typing import List, Type, Dict, Union

from kag.builder.component.reader.markdown_reader import MarkDownReader
from kag.builder.model.chunk import Chunk
from kag.interface.builder.reader_abc import SourceReaderABC
from knext.common.base.runnable import Input, Output

from kag.common.llm.client import LLMClient


class JSONReader(SourceReaderABC):
    """
    A class for reading JSON files, inheriting from `SourceReader`.
    Supports converting JSON data into either a list of dictionaries or a list of Chunk objects.

    Args:
        output_types (Output): Specifies the output type, which can be "Dict" or "Chunk".
        **kwargs: Additional keyword arguments passed to the parent class constructor.
    """

    def __init__(self, output_type="Chunk", **kwargs):
        super().__init__(**kwargs)
        if output_type == "Dict":
            self.output_types = Dict[str, str]
        else:
            self.output_types = Chunk
        self.id_col = kwargs.get("id_col", "id")
        self.name_col = kwargs.get("name_col", "name")
        self.content_col = kwargs.get("content_col", "content")

    @property
    def input_types(self) -> Type[Input]:
        return str

    @property
    def output_types(self) -> Type[Output]:
        return self._output_types

    @output_types.setter
    def output_types(self, output_types):
        self._output_types = output_types

    @staticmethod
    def _read_from_file(file_path: str) -> Union[dict, list]:
        """
        Safely reads JSON from a file and returns its content.

        Args:
            file_path (str): The path to the JSON file.

        Returns:
            Union[dict, list]: The parsed JSON content.

        Raises:
            ValueError: If there is an error reading the JSON file.
        """
        try:
            with open(file_path, "r") as file:
                return json.load(file)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error reading JSON from file: {e}")
        except FileNotFoundError as e:
            raise ValueError(f"File not found: {e}")

    @staticmethod
    def _parse_json_string(json_string: str) -> Union[dict, list]:
        """
        Parses a JSON string and returns its content.

        Args:
            json_string (str): The JSON string to parse.

        Returns:
            Union[dict, list]: The parsed JSON content.

        Raises:
            ValueError: If there is an error parsing the JSON string.
        """
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON string: {e}")

    def invoke(self, input: str, **kwargs) -> List[Output]:
        """
        Parses the input string data and generates a list of Chunk objects or returns the original data.

        This method supports receiving JSON-formatted strings. It extracts specific fields based on provided keyword arguments.
        It can read from a file or directly parse a string. If the input data is in the expected format, it generates a list of Chunk objects;
        otherwise, it throws a ValueError if the input is not a JSON array or object.

        Args:
            input (str): The input data, which can be a JSON string or a file path.
            **kwargs: Keyword arguments used to specify the field names for ID, name, and content.

        Returns:
            List[Output]: A list of Chunk objects or the original data.

        Raises:
            ValueError: If the input data format is incorrect or parsing fails.
        """

        id_col = kwargs.get("id_col", "id")
        name_col = kwargs.get("name_col", "name")
        content_col = kwargs.get("content_col", "content")
        self.id_col = id_col
        self.name_col = name_col
        self.content_col = content_col
        try:
            if os.path.exists(input):
                corpus = self._read_from_file(input)
            else:
                corpus = self._parse_json_string(input)
        except ValueError as e:
            raise e

        if not isinstance(corpus, (list, dict)):
            raise ValueError("Expected input to be a JSON array or object")

        if isinstance(corpus, dict):
            corpus = [corpus]

        if self.output_types == Chunk:
            chunks = []
            basename, _ = os.path.splitext(os.path.basename(input))
            for idx, item in enumerate(corpus):
                if not isinstance(item, dict):
                    continue

                chunk = Chunk(
                    id=item.get(self.id_col) or Chunk.generate_hash_id(f"{input}#{idx}"),
                    name=item.get(self.name_col) or f"{basename}#{idx}",
                    content=item.get(self.content_col),
                )
                chunks.append(chunk)

            return chunks
        else:
            return corpus

if __name__ == "__main__":
    reader = JSONReader()
    json_string = '''[
            {
                "title": "test_json", 
                "text": "Test content"
            }
        ]'''
    chunks = reader.invoke(json_string,name_column="title",content_col = "text")
    res = 1