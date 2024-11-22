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
from kag.interface import SourceReaderABC
from knext.common.base.runnable import Input, Output


@SourceReaderABC.register("csv")
class CSVReader(SourceReaderABC):
    """
    A class for reading CSV files, inheriting from `SourceReader`.
    Supports converting CSV data into either a list of dictionaries or a list of Chunk objects.

    Args:
        output_type (Output): Specifies the output type, which can be "Dict" or "Chunk".
        **kwargs: Additional keyword arguments passed to the parent class constructor.
    """

    @property
    def input_types(self) -> Input:
        return str

    @property
    def output_types(self) -> Output:
        return Dict

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        data = pd.read_csv(input, dtype=str)
        return data.to_dict(orient="records")
