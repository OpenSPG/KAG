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

import json
import os
from typing import List, Type, Dict


from kag.interface import SourceReaderABC
from knext.common.base.runnable import Input, Output


@SourceReaderABC.register("hotpotqa")
class HotpotqaCorpusReader(SourceReaderABC):
    @property
    def input_types(self) -> Type[Input]:
        """The type of input this Runnable object accepts specified as a type annotation."""
        return str

    @property
    def output_types(self) -> Type[Output]:
        """The type of output this Runnable object produces specified as a type annotation."""
        return Dict

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        if os.path.exists(str(input)):
            with open(input, "r") as f:
                corpus = json.load(f)
        else:
            corpus = json.loads(input)

        data = []
        for item_key, item_value in corpus.items():
            data.append(
                {"id": item_key, "name": item_key, "content": "\n".join(item_value)}
            )
        return data


@SourceReaderABC.register("musique")
@SourceReaderABC.register("2wiki")
class MusiqueCorpusReader(SourceReaderABC):
    @property
    def input_types(self) -> Type[Input]:
        """The type of input this Runnable object accepts specified as a type annotation."""
        return str

    @property
    def output_types(self) -> Type[Output]:
        """The type of output this Runnable object produces specified as a type annotation."""
        return Dict

    def get_basename(self, file_name: str):
        base, _ = os.path.splitext(os.path.basename(file_name))
        return base

    def load_data(self, input: Input, **kwargs) -> List[Output]:

        with open(input, "r") as f:
            corpus = json.load(f)
        data = []

        for idx, item in enumerate(corpus):
            title = item["title"]
            content = item["text"]
            data.append(
                {
                    "id": f"{title}#{idx}",
                    "name": title,
                    "content": content,
                }
            )
        return data
