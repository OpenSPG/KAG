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
from typing import List

from kag.interface import ScannerABC
from knext.common.base.runnable import Input, Output


@ScannerABC.register("file")
@ScannerABC.register("file_scanner")
class FileScanner(ScannerABC):
    """
    A class for reading single file and returning the path, inheriting from `ScannerABC`.

    This class is responsible for reading SINGLE file and returning the path as a list of strings.
    It inherits from `ScannerABC` and overrides the necessary methods to handle file-specific operations.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def input_types(self) -> Input:
        return str

    @property
    def output_types(self) -> Output:
        return str

    def load_data(self, input: Input) -> List[Output]:
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

            local_file_path = os.path.join(
                self.kag_project_config.ckpt_dir, "file_scanner"
            )
            if not os.path.exists(local_file_path):
                os.makedirs(local_file_path)
            from urllib.parse import urlparse

            parsed_url = urlparse(input)
            local_file = os.path.join(
                local_file_path, os.path.basename(parsed_url.path)
            )
            local_file = download_from_http(input, local_file)
            return [local_file]

        return [input]
