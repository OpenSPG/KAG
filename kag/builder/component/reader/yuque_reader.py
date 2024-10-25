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

import requests
from typing import Type, List

from kag.builder.component.reader import MarkDownReader
from kag.builder.model.chunk import Chunk
from kag.interface.builder import SourceReaderABC
from knext.common.base.runnable import Input, Output

from kag.common.llm.client import LLMClient


class YuqueReader(SourceReaderABC):
    def __init__(self, token: str, **kwargs):
        super().__init__(**kwargs)
        self.token = token
        self.markdown_reader = MarkDownReader(**kwargs)

    @property
    def input_types(self) -> Type[Input]:
        """The type of input this Runnable object accepts specified as a type annotation."""
        return str

    @property
    def output_types(self) -> Type[Output]:
        """The type of output this Runnable object produces specified as a type annotation."""
        return Chunk

    @staticmethod
    def get_yuque_api_data(token, url):
        headers = {"X-Auth-Token": token}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
            return response.json()["data"]  # Assuming the API returns JSON data
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as err:
            print(f"Error occurred: {err}")
        except Exception as err:
            print(f"An error occurred: {err}")

    def invoke(self, input: str, **kwargs) -> List[Output]:
        if not input:
            raise ValueError("Input cannot be empty")

        url: str = input
        data = self.get_yuque_api_data(self.token, url)
        id = data.get("id", "")
        title = data.get("title", "")
        content = data.get("body", "")

        chunks = self.markdown_reader.solve_content(id, title, content)

        return chunks