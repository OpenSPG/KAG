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


from kag.interface import ScannerABC
from knext.common.base.runnable import Input, Output


@ScannerABC.register("hotpotqa")
@ScannerABC.register("hotpotqa_dataset_scanner")
class HotpotqaCorpusScanner(ScannerABC):
    """
    A class for reading HotpotQA dataset and converting it into a list of dictionaries, inheriting from `ScannerABC`.

    This class is responsible for reading HotpotQA corpus and converting it into a list of dictionaries.
    It inherits from `ScannerABC` and overrides the necessary methods to handle HotpotQA-specific operations.
    """

    @property
    def input_types(self) -> Type[Input]:
        return str

    @property
    def output_types(self) -> Type[Output]:
        return Dict

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        """
        Loads data from a HotpotQA corpus file or JSON string and returns it as a list of dictionaries.

        This method reads HotpotQA corpus data from a file or parses a JSON string and returns it as a list of dictionaries.
        If the input is a file path, it reads the file; if the input is a JSON string, it parses the string.

        Args:
            input (Input): The HotpotQA corpus file path or JSON string to load.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of dictionaries, where each dictionary represents a HotpotQA item.
        """
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


@ScannerABC.register("musique")
@ScannerABC.register("2wiki")
@ScannerABC.register("musique_dataset_scanner")
@ScannerABC.register("2wiki_dataset_scanner")
class MusiqueCorpusScanner(ScannerABC):
    """
    A class for reading Musique/2Wiki dataset and converting it into a list of dictionaries, inheriting from `ScannerABC`.

    This class is responsible for reading Musique/2Wiki corpus and converting it into a list of dictionaries.
    It inherits from `ScannerABC` and overrides the necessary methods to handle Musique/2Wiki-specific operations.
    """

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
        """
        Loads data from a Musique/2Wiki corpus file or JSON string and returns it as a list of dictionaries.

        This method reads Musique/2Wiki corpus data from a file or parses a JSON string and returns it as a list of dictionaries.
        If the input is a file path, it reads the file; if the input is a JSON string, it parses the string.

        Args:
            input (Input): The Musique/2Wiki corpus file path or JSON string to load.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of dictionaries, where each dictionary represents a Musique/2Wiki item.
        """

        if os.path.exists(input):
            with open(input, "r") as f:
                corpus = json.load(f)
        else:
            corpus = json.loads(input)

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
