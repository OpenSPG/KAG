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
    Invoke OpenAI or OpenAI-compatible embedding services to turn texts into embedding vectors.
    """

    def __init__(
        self,
        vector_dimensions: int = None,
    ):
        super().__init__(vector_dimensions)

    def vectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorize a text string into an embedding vector or multiple text strings into
        multiple embedding vectors.

        :param texts: texts to vectorize
        :type texts: str or Iterable[str]
        :return: embedding vectors of the texts
        :rtype: EmbeddingVector or Iterable[EmbeddingVector]
        """
        if isinstance(texts, str):
            return np.random.rand(self._vector_dimensions).tolist()
        else:
            return np.random.rand(len(texts), self._vector_dimensions).tolist()
