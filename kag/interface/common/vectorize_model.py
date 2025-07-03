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
import asyncio
import threading

from tenacity import retry, stop_after_attempt
from kag.common.rate_limiter import RATE_LIMITER_MANGER
from kag.common.registry import Registrable
from typing import Union, Iterable, Mapping

EmbeddingVector = Iterable[float]
SparseEmbeddingVector = Union[Mapping[str, float], str]
logger = logging.getLogger()


@Registrable.register("vectorize_model")
class VectorizeModelABC(Registrable):
    """
    An abstract base class that defines the interface for converting text into embedding vectors.
    """

    _instances = {}
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if "api_key" in kwargs:
            pass
        else:
            kwargs["api_key"] = "abc123"
        key = cls.generate_key(*args, **kwargs)

        if key in cls._instances:
            return cls._instances[key]

        instance = super().__new__(cls)
        cls._instances[key] = instance
        return instance

    def __init__(
        self,
        name: str,
        vector_dimensions: int = None,
        max_rate: float = 1000,
        time_period: float = 1,
    ):
        """
        Initializes the VectorizeModelABC instance.

        Args:
            vector_dimensions (int, optional): The number of dimensions for the embedding vectors. Defaults to None.
        """
        self._vector_dimensions = vector_dimensions
        self.limiter = RATE_LIMITER_MANGER.get_rate_limiter(name, max_rate, time_period)

    def _download_model(self, path, url):
        """
        Downloads a model from a specified URL and extracts it to a given path.

        Args:
            path (str): The directory path to save the downloaded model.
            url (str): The URL from which to download the model.

        Raises:
            RuntimeError: If the model configuration file is not found at the specified path.
        """
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
        Retrieves the dimension of the generated embedding vectors.

        Returns:
            int: The number of dimensions for the embedding vectors.

        Raises:
            RuntimeError: If the embedding service is not available.
        """
        if hasattr(self, "_vector_dimensions"):
            return int(self._vector_dimensions)
        try:
            example_input = "This is a test."
            example_vector = self.vectorize(example_input)
            self._vector_dimensions = len(example_vector)
            return self._vector_dimensions

        except Exception as ex:
            message = "the embedding service is not available"
            raise RuntimeError(message) from ex

    @classmethod
    def generate_key(cls, *args, **kwargs) -> str:
        return f"{cls}"

    @retry(stop=stop_after_attempt(3), reraise=True)
    def vectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorizes text(s) into embedding vector(s).

        Args:
            texts (Union[str, Iterable[str]]): The text or texts to vectorize.

        Returns:
            Union[EmbeddingVector, Iterable[EmbeddingVector]]: The embedding vector(s) of the text(s).

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        message = "abstract method vectorize is not implemented"
        raise NotImplementedError(message)

    @retry(stop=stop_after_attempt(3), reraise=True)
    async def avectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorizes text(s) into embedding vector(s).

        Args:
            texts (Union[str, Iterable[str]]): The text or texts to vectorize.

        Returns:
            Union[EmbeddingVector, Iterable[EmbeddingVector]]: The embedding vector(s) of the text(s).

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """

        async with self.limiter:
            return await asyncio.to_thread(lambda: self.vectorize(texts))


@Registrable.register("sparse_vectorize_model")
class SparseVectorizeModelABC(Registrable):
    """
    An abstract base class that defines the interface for converting text into sparse embedding vectors.
    """

    _instances = {}
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        key = cls.generate_key(*args, **kwargs)

        if key in cls._instances:
            return cls._instances[key]

        instance = super().__new__(cls)
        cls._instances[key] = instance
        return instance

    def __init__(
        self,
        name: str,
        max_rate: float = 1000,
        time_period: float = 1,
    ):
        """
        Initializes the SparseVectorizeModelABC instance.
        """
        self.limiter = RATE_LIMITER_MANGER.get_rate_limiter(name, max_rate, time_period)

    def _download_model(self, path, url):
        """
        Downloads a model from a specified URL and extracts it to a given path.

        Args:
            path (str): The directory path to save the downloaded model.
            url (str): The URL from which to download the model.

        Raises:
            RuntimeError: If the model configuration file is not found at the specified path.
        """
        logger.info(f"download model from:\n{url} to:\n{path}")
        res = requests.get(url)
        with io.BytesIO(res.content) as fileobj:
            with tarfile.open(fileobj=fileobj) as tar:
                tar.extractall(path=path)
        config_path = os.path.join(path, "config.json")
        if not os.path.isfile(config_path):
            message = f"model config not found at {config_path!r}, url {url!r} specified an invalid model"
            raise RuntimeError(message)

    @classmethod
    def generate_key(cls, *args, **kwargs) -> str:
        return f"{cls}"

    @retry(stop=stop_after_attempt(3), reraise=True)
    def vectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[SparseEmbeddingVector, Iterable[SparseEmbeddingVector]]:
        """
        Vectorizes text(s) into sparse embedding vector(s).

        Args:
            texts (Union[str, Iterable[str]]): The text or texts to vectorize.

        Returns:
            Union[SparseEmbeddingVector, Iterable[SparseEmbeddingVector]]: The sparse embedding vector(s) of the text(s).

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        message = "abstract method vectorize is not implemented"
        raise NotImplementedError(message)

    @retry(stop=stop_after_attempt(3), reraise=True)
    async def avectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[SparseEmbeddingVector, Iterable[SparseEmbeddingVector]]:
        """
        Vectorizes text(s) into sparse embedding vector(s).

        Args:
            texts (Union[str, Iterable[str]]): The text or texts to vectorize.

        Returns:
            Union[SparseEmbeddingVector, Iterable[SparseEmbeddingVector]]: The sparse embedding vector(s) of the text(s).

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """

        async with self.limiter:
            return await asyncio.to_thread(lambda: self.vectorize(texts))
