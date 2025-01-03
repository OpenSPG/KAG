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
import requests
from typing import Type, List, Union

# from kag.builder.component.reader.markdown_reader import MarkDownReader
from kag.interface import ScannerABC
from knext.common.base.runnable import Input, Output


@ScannerABC.register("yuque")
@ScannerABC.register("yuque_scanner")
class YuqueScanner(ScannerABC):
    """
    A class for reading data from Yuque, a Chinese documentation platform, inheriting from `ScannerABC`.

    This class is responsible for reading the Yuque knowledge base and return the urls of the documents it contains.
    It can be used in conjunction with the Yuque parser to convert Yuque documents into Chunks.

    It inherits from `ScannerABC` and overrides the necessary methods to handle Yuque-specific operations.

    Args:
        token (str): The authentication token for accessing Yuque API.
        rank (int, optional): The rank of the current worker. Defaults to 0.
        world_size (int, optional): The total number of workers. Defaults to 1.
    """

    def __init__(self, token: str):
        """
        Initializes the YuqueScanner with the specified token, rank, and world size.

        Args:
            token (str): The authentication token for accessing Yuque API.
            rank (int, optional): The rank of the current worker. Defaults to 0.
            world_size (int, optional): The total number of workers. Defaults to 1.
        """
        super().__init__()
        self.token = token

    @property
    def input_types(self) -> Type[Input]:
        """The type of input this Runnable object accepts specified as a type annotation."""
        return Union[str, List[str]]

    @property
    def output_types(self) -> Type[Output]:
        """The type of output this Runnable object produces specified as a type annotation."""
        return str

    def get_yuque_api_data(self, url):
        """
        Fetches data from the Yuque API using the specified URL and authentication token.

        Args:
            url (str): The URL to fetch data from.

        Returns:
            dict: The JSON data returned by the Yuque API.

        Raises:
            HTTPError: If the API returns a bad response (4xx or 5xx).
        """
        headers = {"X-Auth-Token": self.token}
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        return response.json()["data"]  # Assuming the API returns JSON data

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        """
        Loads data from the Yuque API and returns it as a list of document url strings.

        This method fetches data from the Yuque API using the provided URL and converts it into a list of strings.
        If the input is a single document url, it returns a list containing the token and URL.
        If the input is a knowledge base, it returns a list of strings where each string contains the token and the URL of each document it contains.

        Args:
            input (Input): The URL to fetch data from.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of strings, where each string contains the token and the URL of each document.
        """
        url = input
        if isinstance(url, str):
            data = self.get_yuque_api_data(url)
            if isinstance(data, dict):
                # for single yuque doc
                return [f"{self.token}@{url}"]
            output = []
            for item in data:
                slug = item["slug"]
                output.append(os.path.join(url, slug))
            return [f"{self.token}@{url}" for url in output]
        else:
            return [f"{self.token}@{x}" for x in url]
