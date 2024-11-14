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

import io
import os
import tarfile
import requests
import logging

from tenacity import retry, stop_after_attempt
from kag.common.registry import Registrable
from typing import Union, Iterable

EmbeddingVector = Iterable[float]
logger = logging.getLogger()


@Registrable.register("vectorize_model")
class VectorizeModelABC(Registrable):
    """
    Vectorize model turns texts into embedding vectors.
    """

    def __init__(self, vector_dimensions: int = None):
        self._vector_dimensions = vector_dimensions

    def _download_model(self, path, url):
        logger.info(f"download model from:\n{url} to:\n{path}")
        res = requests.get(url)
        with io.BytesIO(res.content) as fileobj:
            with tarfile.open(fileobj=fileobj) as tar:
                tar.extractall(path=path)
        config_path = os.path.join(path, "config.json")
        if not os.path.isfile(config_path):
            message = f"model config not found at {config_path!r}, url {url!r} specified an invalid model"
            raise RuntimeError(message)

    def get_vector_dimensions(self):
        """
        Dimension of generated embedding vectors.
        """
        if self._vector_dimensions is not None:
            return int(self._vector_dimensions)
        try:
            example_input = "This is a test."
            example_vector = self.vectorize(example_input)
            self._vector_dimensions = len(example_vector)
            return self._vector_dimensions

        except Exception as ex:
            message = "the embedding service is not available"
            raise RuntimeError(message) from ex

    @retry(stop=stop_after_attempt(3))
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
        message = "abstract method vectorize is not implemented"
        raise NotImplementedError(message)
