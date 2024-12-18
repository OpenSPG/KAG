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

import pandas as pd
from kag.interface import ScannerABC
from kag.common.utils import generate_hash_id
from knext.common.base.runnable import Input, Output


@ScannerABC.register("csv")
class CSVScanner(ScannerABC):
    """
    A class for reading CSV files and converting them into a list of dictionaries.

    This class inherits from `ScannerABC` and provides functionality to read CSV files.
    It can either return the entire row as a dictionary or split the row into multiple dictionaries
    based on specified columns.

    Attributes:
        cols (List[str]): A list of column names to be processed. If None, the entire row is returned as a dictionary.
        rank (int): The rank of the current process (used for distributed processing).
        world_size (int): The total number of processes (used for distributed processing).
    """

    def __init__(self, cols: List[str] = None, rank: int = 0, world_size: int = 1):
        """
        Initializes the CSVScanner with optional columns, rank, and world size.

        Args:
            cols (List[str], optional): A list of column names to be processed. Defaults to None.
                - If not specified, each row of the CSV file will be returned as a single dictionary.
                - If specified, each row will be split into multiple dictionaries, one for each specified column.
            rank (int, optional): The rank of the current process. Defaults to None.
            world_size (int, optional): The total number of processes. Defaults to None.
        """
        super().__init__(rank=rank, world_size=world_size)
        self.cols = cols

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
        data = pd.read_csv(input, dtype=str)
        if self.cols is None:
            return data.to_dict(orient="records")

        contents = []
        for _, row in data.iterrows():
            for k, v in row.items():
                if k in self.cols:
                    v = str(v)
                    name = v[:5] + "..." + v[-5:]
                    contents.append(
                        {"id": generate_hash_id(v), "name": name, "content": v}
                    )

        return contents
