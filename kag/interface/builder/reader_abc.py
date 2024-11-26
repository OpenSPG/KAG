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
from abc import ABC, abstractmethod
from typing import Any, Generator, List
from kag.interface.builder.base import BuilderComponent
from kag.common.sharding_info import ShardingInfo
from knext.common.base.runnable import Input, Output


class SourceReaderABC(BuilderComponent, ABC):
    """
    Interface for reading files into a list of unstructured chunks or structured dicts.
    """

    def __init__(self, rank: int = None, world_size: int = None):
        if rank is None or world_size is None:
            from kag.common.env import get_rank, get_world_size

            rank = get_rank(0)
            world_size = get_world_size(1)
        self.sharding_info = ShardingInfo(shard_id=rank, shard_count=world_size)

    @property
    def input_types(self) -> Input:
        return str

    @property
    def output_types(self) -> Output:
        return Any

    @abstractmethod
    def load_data(self, input: Input, **kwargs) -> List[Output]:
        raise NotImplementedError("load not implemented yet.")

    def _generate(self, data):
        start, end = self.sharding_info.get_sharding_range(len(data))
        worker = (
            f"{self.sharding_info.get_rank()}/{self.sharding_info.get_world_size()}"
        )
        msg = (
            f"There are total {len(data)} data to process, worker "
            f"{worker} will process range [{start}, {end})"
        )

        print(msg)
        for item in data[start:end]:
            yield item

    def generate(self, input: Input, **kwargs) -> Generator[Output, Input, None]:
        data = self.load_data(input, **kwargs)
        for item in self._generate(data):
            yield item

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        return list(self.generate(input, **kwargs))
