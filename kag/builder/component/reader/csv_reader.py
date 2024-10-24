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
from typing import List, Type, Dict

import pandas as pd

from kag.builder.model.chunk import Chunk
from kag.interface.builder.reader_abc import SourceReaderABC
from knext.common.base.runnable import Input, Output


class CSVReader(SourceReaderABC):
    """
    A class for reading CSV files, inheriting from `SourceReader`.
    Supports converting CSV data into either a list of dictionaries or a list of Chunk objects.

    Args:
        output_type (Output): Specifies the output type, which can be "Dict" or "Chunk".
        **kwargs: Additional keyword arguments passed to the parent class constructor.
    """

    def __init__(self, output_type="Chunk", **kwargs):
        super().__init__(**kwargs)
        if output_type == "Dict":
            self.output_types = Dict[str, str]
        else:
            self.output_types = Chunk
        self.id_col = kwargs.get("id_col", "id")
        self.name_col = kwargs.get("name_col", "name")
        self.content_col = kwargs.get("content_col", "content")

    @property
    def input_types(self) -> Type[Input]:
        return str

    @property
    def output_types(self) -> Type[Output]:
        return self._output_types

    @output_types.setter
    def output_types(self, output_types):
        self._output_types = output_types

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Reads a CSV file and converts the data format based on the output type.

        Args:
            input (Input): Input parameter, expected to be a string representing the path to the CSV file.
            **kwargs: Additional keyword arguments, which may include `id_column`, `name_column`, `content_column`, etc.

        Returns:
            List[Output]:
                - If `output_types` is `Chunk`, returns a list of Chunk objects.
                - If `output_types` is `Dict`, returns a list of dictionaries.
        """

        try:
            data = pd.read_csv(input)
            data = data.astype(str)
        except Exception as e:
            raise IOError(f"Failed to read the file: {e}")

        if self.output_types == Chunk:
            chunks = []
            basename, _ = os.path.splitext(os.path.basename(input))
            for idx, row in enumerate(data.to_dict(orient="records")):
                kwargs = {k: v for k, v in row.items() if k not in [self.id_col, self.name_col, self.content_col]}
                chunks.append(
                    Chunk(
                        id=row.get(self.id_col) or Chunk.generate_hash_id(f"{input}#{idx}"),
                        name=row.get(self.name_col) or f"{basename}#{idx}",
                        content=row[self.content_col],
                        **kwargs
                    )
                )
            return chunks
        else:
            return data.to_dict(orient="records")
