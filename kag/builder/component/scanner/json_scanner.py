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

from kag.interface import ScannerABC
from knext.common.base.runnable import Input, Output


@ScannerABC.register("json")
@ScannerABC.register("json_scanner")
class JSONScanner(ScannerABC):
    """
    A class for reading JSON files or parsing JSON-formatted strings into a list of dictionaries, inheriting from `ScannerABC`.

    This class is responsible for reading JSON files or parsing JSON-formatted strings and converting them into a list of dictionaries.
    It inherits from `ScannerABC` and overrides the necessary methods to handle JSON-specific operations.

    Note: The JSON data must be a list of dictionaries.
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
        Reads JSON data from a file and returns it as a list of dictionaries.

        Args:
            file_path (str): The path to the JSON file.

        Returns:
            List[Dict]: The JSON data loaded from the file.

        Raises:
            ValueError: If there is an error reading the JSON from the file or if the file is not found.
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
        Parses a JSON string and returns it as a list of dictionaries.

        Args:
            json_string (str): The JSON string to parse.

        Returns:
            List[Dict]: The parsed JSON data.

        Raises:
            ValueError: If there is an error parsing the JSON string.
        """
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON string: {e}")

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        """
        Loads data from a JSON file or JSON string and returns it as a list of dictionaries.

        This method reads JSON data from a file or parses a JSON string and returns it as a list of dictionaries.
        If the input is a file path, it reads the file; if the input is a JSON string, it parses the string.

        Args:
            input (Input): The JSON file path or JSON string to load.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of dictionaries, where each dictionary represents a JSON object.

        Raises:
            ValueError: If there is an error reading the JSON data or if the input is not a valid JSON array or object.
        """
        input = self.download_data(input)
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

        # Handle data sharding if multiple shards are specified
        if self.sharding_info.shard_count > 1:
            total_items = len(corpus)
            shard_size = total_items // self.sharding_info.shard_count
            start_idx = self.sharding_info.shard_id * shard_size
            end_idx = (
                start_idx + shard_size
                if self.sharding_info.shard_id < self.sharding_info.shard_count - 1
                else total_items
            )
            corpus = corpus[start_idx:end_idx]

        return corpus
