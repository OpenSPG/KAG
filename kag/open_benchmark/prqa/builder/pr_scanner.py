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
from typing import Dict, List

from kag.interface import ScannerABC
from knext.common.base.runnable import Input, Output


@ScannerABC.register("pr_scanner")
class PRScanner(ScannerABC):
    def __init__(
        self,
        header: bool = True,
        col_names: List[str] = None,
        col_ids: List[int] = None,
        rank: int = 0,
        world_size: int = 1,
    ):
        super().__init__(rank=rank, world_size=world_size)
        self.header = header
        self.col_names = col_names
        self.col_ids = col_ids

    @property
    def input_types(self) -> Input:
        return str

    @property
    def output_types(self) -> Output:
        return Dict

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        """
        Loads data from a CSV file and converts it into a list of dictionaries.

        Args:
            input (Input): The input file path to the CSV file.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of dictionaries containing the processed data.
        """
        data = []
        with open(input, "r") as f:
            for line in f:
                # Split each line by tab character
                parts = line.strip().split("\t")
                if len(parts) == 3:
                    # Convert to dictionary
                    data.append(
                        {"subject": parts[0], "relation": parts[1], "object": parts[2]}
                    )

        return data
