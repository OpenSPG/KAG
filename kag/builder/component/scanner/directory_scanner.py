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
import re
from typing import List

from kag.interface import ScannerABC

from knext.common.base.runnable import Input, Output


@ScannerABC.register("dir")
@ScannerABC.register("dir_file_scanner")
class DirectoryScanner(ScannerABC):
    """
    A class for reading files from a directory based on a specified file pattern or suffix, inheriting from `ScannerABC`.
    It can be used in conjunction with the parsers such as PDF/MarkDown parser to convert files into Chunks.

    This class is responsible for reading files from a directory and returning a list of file paths that match the specified file pattern/suffix.
    It inherits from `ScannerABC` and overrides the necessary methods to handle directory-specific operations.

    """

    def __init__(
        self,
        file_pattern: str = None,
        file_suffix: str = None,
        rank: int = 0,
        world_size: int = 1,
    ):
        """
        Initializes the DirectoryScanner with the specified file pattern, file suffix, rank, and world size.

        Args:
            file_pattern (str, optional): The regex pattern to match file names. Defaults to None.
            file_suffix (str, optional): The file suffix to match if `file_pattern` is not provided. Defaults to None.
            rank (int, optional): The rank of the current worker. Defaults to 0.
            world_size (int, optional): The total number of workers. Defaults to 1.
        """
        super().__init__(rank=rank, world_size=world_size)
        if file_pattern is None:
            if file_suffix:
                file_pattern = f".*{file_suffix}$"
            else:
                file_pattern = r".*txt$"
        self.file_pattern = re.compile(file_pattern)

    @property
    def input_types(self) -> Input:
        return str

    @property
    def output_types(self) -> Output:
        return str

    def find_files_by_regex(self, directory):
        """
        Finds files in the specified directory that match the file pattern.

        Args:
            directory (str): The directory to search for files.

        Returns:
            List[str]: A list of file paths that match the file pattern.
        """
        matched_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if self.file_pattern.match(file):
                    file_path = os.path.join(root, file)
                    matched_files.append(file_path)
        return matched_files

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        """
        Loads data by finding files in the specified directory that match the file pattern.

        This method searches the directory specified by the input and returns a list of file paths that match the file pattern.

        Args:
            input (Input): The directory to search for files.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of file paths that match the file pattern.
        """
        return self.find_files_by_regex(input)
