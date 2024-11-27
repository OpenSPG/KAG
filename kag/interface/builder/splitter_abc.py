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
from kag.builder.model.chunk import Chunk
from knext.common.base.runnable import Input, Output


class SplitterABC(BuilderComponent, ABC):
    """
    Abstract base class for splitting a chunk into a list of smaller chunks.

    This class defines the interface for splitting a chunk into smaller chunks.
    It inherits from BuilderComponent and ABC, ensuring that any subclass must implement
    the `invoke` method.
    """

    @property
    def input_types(self) -> Input:
        return Chunk

    @property
    def output_types(self) -> Output:
        return Chunk

    @abstractmethod
    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Abstract method to be implemented by subclasses for splitting a chunk.

        Args:
            input (Input): The chunk to be split.
            **kwargs: Additional keyword arguments, currently unused but kept for potential future expansion.

        Returns:
            List[Output]: A list of smaller chunks resulting from the split operation.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """
        raise NotImplementedError(
            f"`invoke` is not currently supported for {self.__class__.__name__}."
        )
