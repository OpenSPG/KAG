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

from typing import Type, List
from kag.interface import SplitterABC
from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.interface.builder.base import KAG_PROJECT_CONF
from kag.common.utils import generate_hash_id
from knext.common.base.runnable import Input, Output
from kag.builder.component.splitter.base_table_splitter import BaseTableSplitter
from kag.builder.component.splitter.length_splitter import LengthSplitter


@SplitterABC.register("line_length_splitter")
class LineLengthSplitter(LengthSplitter):
    def __init__(
        self,
        split_length: int = 500,
        window_length: int = 100,
        is_split_table: bool = False,
    ):
        super().__init__(
            split_length=split_length,
            window_length=window_length,
            is_split_table=is_split_table,
        )

    def split_sentence(self, content):
        """
        Splits the given content into sentences based on delimiters.

        Args:
            content (str): The content to be split into sentences.

        Returns:
            List[str]: A list of sentences.
        """
        sentence_delimiters = (
            "\n" if KAG_PROJECT_CONF.language == "en" else "\n"
        )
        output = []
        start = 0
        for idx, char in enumerate(content):
            if char in sentence_delimiters:
                end = idx
                tmp = content[start : end + 1].strip()
                if len(tmp) > 0:
                    output.append(tmp.strip())
                start = idx + 1
        res = content[start:].strip()
        if len(res) > 0:
            output.append(res)
        return output
