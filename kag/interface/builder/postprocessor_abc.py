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
from typing import List

from kag.interface.builder.base import BuilderComponent
from kag.builder.model.sub_graph import SubGraph
from knext.common.base.runnable import Input, Output


class PostProcessorABC(BuilderComponent):
    """
    Abstract base class for post-processing subgraphs.

    This class defines the interface for post-processing operations on subgraphs.
    """

    @property
    def input_types(self):
        return SubGraph

    @property
    def output_types(self):
        return SubGraph

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Abstract method to be implemented by subclasses. It processes the input subgraph and returns a list of modified subgraphs.

        Args:
            input (Input): The input subgraph to be processed.
            **kwargs: Additional keyword arguments.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.

        Returns:
            List[Output]: A list of modified subgraphs.
        """
        raise NotImplementedError(
            f"`invoke` is not currently supported for {self.__class__.__name__}."
        )