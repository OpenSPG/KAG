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


class VectorizerABC(BuilderComponent):
    """
    Abstract base class for generating embedding vectors for node attributes in a graph.

    This class defines the interface for generating embedding vectors for node attributes
    in a SubGraph. It inherits from BuilderComponent, ensuring that any subclass must implement
    the `invoke` method.
    """

    @property
    def input_types(self):
        return SubGraph

    @property
    def output_types(self):
        return SubGraph

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Abstract method to be implemented by subclasses for generating embedding vectors.

        Args:
            input (Input): The SubGraph for which to generate embedding vectors.
            **kwargs: Additional keyword arguments, currently unused but kept for potential future expansion.

        Returns:
            List[Output]: A list of output objects (SubGraphs) with generated embedding vectors inserted.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """
        raise NotImplementedError(
            f"`invoke` is not currently supported for {self.__class__.__name__}."
        )
