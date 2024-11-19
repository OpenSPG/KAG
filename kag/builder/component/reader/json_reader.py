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
from typing import Union, Dict, List

from kag.interface import SourceReaderABC
from knext.common.base.runnable import Input, Output


@SourceReaderABC.register("json")
class JSONReader(SourceReaderABC):
    """
    A class for reading JSON files, inheriting from `SourceReaderABC`.
    """

    @property
    def input_types(self) -> Input:
        return str

    @property
    def output_types(self) -> Output:
        return Dict

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

    def load_data(self, input: Input, **kwargs) -> List[Output]:
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
        return corpus
