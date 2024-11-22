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
from kag.interface import RecordParserABC
from knext.common.base.runnable import Output, Input
from kag.builder.model.chunk import Chunk


@RecordParserABC.register("dict")
class DictParser(RecordParserABC):
    """
    A class for convert dict object to chunks, inheriting from `RecordParserABC`.

    Args:
        cut_depth (int): The depth of cutting, determining the level of detail in parsing. Default is 1.
    """

    def __init__(
        self, id_col: str = "id", name_col: str = "name", content_col: str = "content"
    ):
        self.id_col = id_col
        self.name_col = name_col
        self.content_col = content_col

    @property
    def input_types(self) -> Input:
        return Dict

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        chunk_id = input.pop(self.id_col)
        chunk_name = input.pop(self.name_col)
        chunk_content = input.pop(self.content_col)
        return [Chunk(id=chunk_id, name=chunk_name, content=chunk_content, **input)]
