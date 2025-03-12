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
@ScannerABC.register("csv_scanner")
class CSVScanner(ScannerABC):
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
        input = self.download_data(input)

        if self.header:
            data = pd.read_csv(input, dtype=str)
        else:
            data = pd.read_csv(input, dtype=str, header=None)

        # 如果有多个分片，根据rank和world_size进行数据分片
        if self.sharding_info.shard_count > 1:
            total_rows = len(data)
            shard_size = total_rows // self.sharding_info.shard_count
            start_idx = self.sharding_info.shard_id * shard_size
            end_idx = (
                start_idx + shard_size
                if self.sharding_info.shard_id < self.sharding_info.shard_count - 1
                else total_rows
            )
            data = data.iloc[start_idx:end_idx]

        if self.col_names:
            col_keys = self.col_names
        elif self.col_ids:
            if self.header:
                all_keys = data.keys().to_list()
                col_keys = [all_keys[x] for x in self.col_ids]
            else:
                col_keys = self.col_ids
        else:
            col_keys = None

        if col_keys is None:
            return data.to_dict(orient="records")

        contents = []
        for _, row in data.iterrows():
            for k, v in row.items():
                if k in col_keys:
                    v = str(v)
                    if len(v) <= 10:
                        name = v
                    else:
                        name = v[:5] + "..." + v[-5:]
                    contents.append(
                        {"id": generate_hash_id(v), "name": name, "content": v}
                    )

        return contents


@ScannerABC.register("csv_structured")
@ScannerABC.register("csv_structured_scanner")
class CSVStructuredScanner(ScannerABC):
    def __init__(
        self,
        header: bool = True,
        col_map: Dict[int, str] = None,
        rank: int = 0,
        world_size: int = 1,
    ):
        super().__init__(rank=rank, world_size=world_size)
        self.header = header
        self.col_map = col_map

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
        input = self.download_data(input)

        if self.header:
            data = pd.read_csv(input, dtype=str)
        else:
            data = pd.read_csv(input, dtype=str, header=None)

        # 如果有多个分片，根据rank和world_size进行数据分片
        if self.sharding_info.shard_count > 1:
            total_rows = len(data)
            shard_size = total_rows // self.sharding_info.shard_count
            start_idx = self.sharding_info.shard_id * shard_size
            end_idx = (
                start_idx + shard_size
                if self.sharding_info.shard_id < self.sharding_info.shard_count - 1
                else total_rows
            )
            data = data.iloc[start_idx:end_idx]

        if self.col_map is None:
            return data.to_dict(orient="records")

        contents = []
        for _, row in data.iterrows():
            renamed_row = {}
            for old_key, new_key in self.col_map.items():
                renamed_row[new_key] = row[old_key]
            contents.append(renamed_row)

        return contents
