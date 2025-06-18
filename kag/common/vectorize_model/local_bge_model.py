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

import os
import logging
import threading
from typing import Union, Iterable
from kag.interface import VectorizeModelABC, EmbeddingVector

logger = logging.getLogger()


LOCAL_MODEL_MAP = {}


@VectorizeModelABC.register("bge")
@VectorizeModelABC.register("bge_vectorize_model")
class LocalBGEVectorizeModel(VectorizeModelABC):
    """
    A class that extends the VectorizeModelABC base class.
    It invokes local BGE embedding models to convert texts into embedding vectors.
    """

    _LOCK = threading.Lock()

    def __init__(
        self,
        path: str,
        url: str = None,
        query_instruction_for_retrieval: str = None,
        vector_dimensions: int = None,
        **kwargs,
    ):
        """
        Initializes the LocalBGEVectorizeModel instance.

        Args:
            path (str): The path to the local BGE model.
            url (str, optional): The URL to download the model if not found locally. Defaults to None.
            query_instruction_for_retrieval (str, optional): The query instruction for retrieval. Defaults to None.
            vector_dimensions (int, optional): The number of dimensions for the embedding vectors. Defaults to None.
        """
        name = self.generate_key()

        super().__init__(name, vector_dimensions)
        self.model_path = os.path.expanduser(path)
        self.url = url
        config_path = os.path.join(self.model_path, "config.json")
        if not os.path.isfile(config_path):
            if url is None:
                message = f"model not found at {path!r}, nor model url specified"
                raise RuntimeError(message)
            logger.info("Model file not found in path, start downloading...")
            self._download_model(self.model_path, self.url)
        default_chinese_query_instruction_for_retrieval = "为这个句子生成表示以用于向量检索："
        default_english_query_instruction_for_retrieval = (
            "Represent this sentence for searching relevant passages:"
        )
        if "BAAI/bge-base-zh-v1.5" in path:
            default_query_instruction_for_retrieval = (
                default_chinese_query_instruction_for_retrieval
            )
        else:
            default_query_instruction_for_retrieval = (
                default_english_query_instruction_for_retrieval
            )

        if query_instruction_for_retrieval:
            self.query_instruction_for_retrieval = query_instruction_for_retrieval
        else:
            self.query_instruction_for_retrieval = (
                default_query_instruction_for_retrieval
            )
        with LocalBGEVectorizeModel._LOCK:
            if self.model_path in LOCAL_MODEL_MAP:
                logger.info("Found existing model, reuse.")
                model = LOCAL_MODEL_MAP[self.model_path]
            else:
                model = self._load_model(self.model_path)
                LOCAL_MODEL_MAP[self.model_path] = model
            self.model = model

    def _load_model(self, path):
        """
        Loads the BGE model from the specified path.

        Args:
            path (str): The path to the BGE model.

        Returns:
            FlagModel: The loaded BGE model.
        """
        # We need to import sklearn at first, otherwise sklearn will fail on macOS with m chip.
        import sklearn  # noqa
        from FlagEmbedding import FlagModel

        logger.info(
            f"Loading FlagModel from {path!r} with query_instruction_for_retrieval={self.query_instruction_for_retrieval!r}"
        )
        model = FlagModel(
            path,
            query_instruction_for_retrieval=self.query_instruction_for_retrieval,
            use_fp16=False,
        )
        return model

    def vectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorizes text(s) into embedding vector(s).

        Args:
            texts (Union[str, Iterable[str]]): The text or texts to vectorize.

        Returns:
            Union[EmbeddingVector, Iterable[EmbeddingVector]]: The embedding vector(s) of the text(s).
        """

        result = self.model.encode(texts)
        return result.tolist()


@VectorizeModelABC.register("bge_m3")
class LocalBGEM3VectorizeModel(VectorizeModelABC):
    """
    A class that extends the VectorizeModelABC base class.
    It invokes local BGE-M3 embedding models to convert texts into embedding vectors.
    """

    _LOCK = threading.Lock()

    def __init__(
        self,
        path: str,
        url: str = None,
        vector_dimensions: int = None,
    ):
        """
        Initializes the LocalBGEM3VectorizeModel instance.

        Args:
            path (str): The path to the local BGE-M3 model.
            url (str, optional): The URL to download the model if not found locally. Defaults to None.
            vector_dimensions (int, optional): The number of dimensions for the embedding vectors. Defaults to None.
        """
        name = self.generate_key()
        super().__init__(name, vector_dimensions)
        self.url = url
        self.model_path = os.path.expanduser(path)
        config_path = os.path.join(self.model_path, "config.json")
        if not os.path.isfile(config_path):
            if url is None:
                message = f"model not found at {path!r}, nor model url specified"
                raise RuntimeError(message)
            self._download_model(path, url)
        with LocalBGEM3VectorizeModel._LOCK:
            if self.model_path in LOCAL_MODEL_MAP:
                logger.info("Found existing model, reuse.")
                model = LOCAL_MODEL_MAP[self.model_path]
            else:
                model = self._load_model(self.model_path)
                LOCAL_MODEL_MAP[self.model_path] = model
            self.model = model

    def _load_model(self, path):
        """
        Loads the BGE-M3 model from the specified path.

        Args:
            path (str): The path to the BGE-M3 model.

        Returns:
            BGEM3FlagModel: The loaded BGE-M3 model.
        """
        # We need to import sklearn at first, otherwise sklearn will fail on macOS with m chip.

        import sklearn  # noqa
        from FlagEmbedding import BGEM3FlagModel

        logger.info(f"Loading BGEM3FlagModel from {path!r}")
        model = BGEM3FlagModel(path, use_fp16=False)
        return model

    def vectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorizes text(s) into embedding vector(s).

        Args:
            texts (Union[str, Iterable[str]]): The text or texts to vectorize.

        Returns:
            Union[EmbeddingVector, Iterable[EmbeddingVector]]: The embedding vector(s) of the text(s).
        """
        result = self.model.encode(texts)["dense_vecs"]
        return result.tolist()
