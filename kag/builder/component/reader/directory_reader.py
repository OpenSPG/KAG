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

from kag.interface import SourceReaderABC

from knext.common.base.runnable import Input, Output


@SourceReaderABC.register("dir")
class DirectoryReader(SourceReaderABC):
    def __init__(
        self,
        file_pattern: str = None,
        file_suffix: str = None,
        rank: int = 0,
        world_size: int = 1,
    ):
        super().__init__(rank, world_size)

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
        matched_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if self.file_pattern.match(file):
                    file_path = os.path.join(root, file)
                    matched_files.append(file_path)
        return matched_files

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        return self.find_files_by_regex(input)
