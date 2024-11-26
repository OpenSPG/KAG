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
    A class for reading CSV files and yielding item rows one by one, inheriting from `SourceReaderABC`.

    This class is responsible for reading CSV files and converting each line into a dictionary.
    It inherits from `SourceReaderABC` and overrides the necessary methods to handle CSV-specific operations.
    """

    @property
    def input_types(self) -> Input:
        return str

    @property
    def output_types(self) -> Output:
        return Dict

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        """
        Loads data from a CSV file and returns it as a list of dictionaries.

        This method reads the CSV file specified by the input and converts it into a list of dictionaries,
        where each dictionary represents a row in the CSV file.

        Args:
            input (Input): The path to the CSV file to load.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of dictionaries, where each dictionary represents a row in the CSV file.
        """
        data = pd.read_csv(input, dtype=str)
        return data.to_dict(orient="records")
