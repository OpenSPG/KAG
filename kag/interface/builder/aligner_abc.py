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
from typing import List

from kag.interface.builder.base import BuilderComponent
from kag.builder.model.sub_graph import SubGraph
from knext.common.base.runnable import Input, Output


class AlignerABC(BuilderComponent, ABC):
    """
    Abstract base class for aligning extractor results to a semantic schema.

    This class defines the interface for aligning the results obtained from
    extractors to a semantic schema. It inherits from `BuilderComponent` and
    is an abstract base class (`ABC`), meaning that concrete implementations
    must be provided for all abstract methods.

    Attributes:
        input_types (SubGraph): The expected input type for the aligner.
        output_types (SubGraph): The output type produced by the aligner.
    """

    @property
    def input_types(self):
        return SubGraph

    @property
    def output_types(self):
        return SubGraph

    @abstractmethod
    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Abstract method to invoke the alignment process.

        This method must be implemented by any concrete subclass. It is
        responsible for aligning the input data to the semantic schema and
        returning the aligned results.

        Args:
            input (Input): The input data to be aligned.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of aligned output objects.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError(
            f"`invoke` is not currently supported for {self.__class__.__name__}."
        )
