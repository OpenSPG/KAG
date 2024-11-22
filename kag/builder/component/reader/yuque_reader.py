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
from typing import Type, List

# from kag.builder.component.reader.markdown_reader import MarkDownReader
from kag.interface import SourceReaderABC
from knext.common.base.runnable import Input, Output


@SourceReaderABC.register("yuque")
class YuqueReader(SourceReaderABC):
    def __init__(self, token: str, rank: int = 0, world_size: int = 1):
        super().__init__(rank, world_size)
        self.token = token

    @property
    def input_types(self) -> Type[Input]:
        """The type of input this Runnable object accepts specified as a type annotation."""
        return str

    @property
    def output_types(self) -> Type[Output]:
        """The type of output this Runnable object produces specified as a type annotation."""
        return str

    def get_yuque_api_data(self, url):
        headers = {"X-Auth-Token": self.token}
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        return response.json()["data"]  # Assuming the API returns JSON data

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        url = input
        data = self.get_yuque_api_data(url)
        if isinstance(data, dict):
            # for single yuque doc
            return [f"{self.token}@{url}"]
        output = []
        for item in data:
            slug = item["slug"]
            output.append(os.path.join(url, slug))
        return [f"{self.token}@{url}" for url in output]
