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
import numpy as np

from typing import Union, Iterable
from kag.interface import VectorizeModelABC, EmbeddingVector


@VectorizeModelABC.register("mock")
class MockVectorizeModel(VectorizeModelABC):
    """
    A mock implementation of the VectorizeModelABC class, used for testing purposes.

    This class provides a method to generate random embedding vectors for given texts.
    """

    def __init__(
        self,
        vector_dimensions: int = None,
        **kwargs,
    ):
        """
        Initializes the MockVectorizeModel instance.

        Args:
            vector_dimensions (int, optional): The number of dimensions for the embedding vectors. Defaults to None.
        """
        name = kwargs.get("name", None)
        if not name:
            name = "mock_vectorize_model"

        super().__init__(name, vector_dimensions)

    def vectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Generates random embedding vectors for the given texts.

        Args:
            texts (Union[str, Iterable[str]]): The text or texts to vectorize.

        Returns:
            Union[EmbeddingVector, Iterable[EmbeddingVector]]: The embedding vector(s) of the text(s).
        """
        if isinstance(texts, str):
            return np.random.rand(self._vector_dimensions).tolist()
        else:
            return np.random.rand(len(texts), self._vector_dimensions).tolist()
