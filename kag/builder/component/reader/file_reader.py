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
from typing import List

from kag.interface import SourceReaderABC

from knext.common.base.runnable import Input, Output


@SourceReaderABC.register("file")
class FileReader(SourceReaderABC):
    """
    A class for reading single file and returning the path, inheriting from `SourceReaderABC`.

    This class is responsible for reading SINGLE file and returning the path as a list of strings.
    It inherits from `SourceReaderABC` and overrides the necessary methods to handle file-specific operations.
    """

    @property
    def input_types(self) -> Input:
        return str

    @property
    def output_types(self) -> Output:
        return str

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        """
        Loads data by returning the input file path as a list of strings.

        This method takes the input file path and returns it as a list containing the file path.

        Args:
            input (Input): The file path to load.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list containing the input file path.
        """
        if input.startswith("http://") or input.startswith("https://"):
            from kag.common.utils import download_from_http

            local_file = download_from_http(input)
            return [local_file]
        return [input]
