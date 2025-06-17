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
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Generator, List
from kag.interface.builder.base import BuilderComponent
from knext.common.base.runnable import Input, Output


class ScannerABC(BuilderComponent, ABC):
    """
    Abstract base class for scanning  raw content from the source,
    typically used in conjunction with downstream parsers to obtain text suitable for knowledge extraction.

    This class defines the interface for components that read input sources such as a directory or csv file.
    It inherits from `BuilderComponent` and `ABC` (Abstract Base Class).

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def input_types(self) -> Input:
        return str

    @property
    def output_types(self) -> Output:
        return Any

    @abstractmethod
    def load_data(self, input: Input) -> List[Output]:
        """
        Abstract method to load data from the input source.

        This method must be implemented by any subclass. It is responsible for loading data from the input source
        and returning a list of processed results.

        Args:
            input (Input): The input source to load data from.

        Returns:
            List[Output]: A list of processed results.

        Raises:
            NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError("load not implemented yet.")

    def _generate(self, data):
        """
        Generates items from the data based on the sharding configuration.

        This method is used internally to generate items from the source based on the sharding configuration.

        Args:
            data: The data to process.

        Yields:
            The items within the sharded range.
        """
        start, end = self.sharding_info.get_sharding_range(len(data))
        worker = (
            f"{self.sharding_info.get_rank()}/{self.sharding_info.get_world_size()}"
        )
        msg = (
            f"[Scanner]: There are total {len(data)} data to process, worker "
            f"{worker} will process range [{start}, {end})"
        )

        print(msg)
        for item in data[start:end]:
            yield item

    def generate(self, input: Input, **kwargs) -> Generator[Output, Input, None]:
        """
        Generates items from the input source based on the sharding configuration.

        This method loads data from the input source and generates items based on the sharding configuration.

        Args:
            input (Input): The input source to load data from.

        Yields:
            The items within the sharded range.
        """
        data = self.load_data(input)
        for item in self._generate(data):
            yield item

    def download_data(self, input: Input) -> List[Output]:
        """
        Downloads data from a given input URL or returns the input directly if it is not a URL.

        Args:
            input (Input): The input source, which can be a URL (starting with "http://" or "https://") or a local path.
            **kwargs: Additional keyword arguments (currently unused).

        Returns:
            List[Output]: A list containing the local file path if the input is a URL, or the input itself if it is not a URL.

        """
        if input.startswith("http://") or input.startswith("https://"):
            from kag.common.utils import download_from_http

            local_file_path = os.path.join(
                self.kag_project_config.ckpt_dir, "file_scanner"
            )
            if not os.path.exists(local_file_path):
                os.makedirs(local_file_path)
            # local_file = os.path.join(local_file_path, os.path.basename(input))
            from urllib.parse import urlparse

            parsed_url = urlparse(input)
            local_file = os.path.join(
                local_file_path, os.path.basename(parsed_url.path)
            )

            local_file = download_from_http(input, local_file)
            return local_file
        return input

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the component to process input data and return a list of processed results.

        This method generates items from the input source and returns them as a list.

        Args:
            input (Input): The input source to load data from.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of processed results.
        """
        return list(self.generate(input, **kwargs))

    async def ainvoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the component to process input data and return a list of processed results.

        This method generates items from the input source and returns them as a list.
        TODO: relpace sync read to async read
        Args:
            input (Input): The input source to load data from.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of processed results.
        """
        return await asyncio.to_thread(lambda: lambda: self.invoke(input, **kwargs))

    def size(self, input):
        if not hasattr(self, "_data_size"):
            self._data_size = len(self.load_data(input))
        return self._data_size

    @property
    def inherit_input_key(self):
        return False
