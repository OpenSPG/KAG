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
from typing import Union, Iterable
from kag.common.vectorizer.vectorizer import Vectorizer, EmbeddingVector

logger = logging.getLogger()


LOCAL_MODEL_MAP = {}


@Vectorizer.register("bge")
class LocalBGEVectorizer(Vectorizer):
    """
    Invoke local bge embedding models to turn texts into embedding vectors.
    """

    def __init__(
        self,
        path: str,
        url: str = None,
        query_instruction_for_retrieval: str = None,
        vector_dimensions: int = None,
    ):
        super().__init__(vector_dimensions)
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

        if self.model_path in LOCAL_MODEL_MAP:
            logger.info("Found existing model, reuse.")
            model = LOCAL_MODEL_MAP[self.model_path]
        else:
            model = self._load_model(self.model_path)
            LOCAL_MODEL_MAP[self.model_path] = model
        self.model = model

    def _load_model(self, path):
        # We need to import sklearn at first, otherwise sklearn will fail on macOS with m chip.
        import sklearn  # noqa
        from FlagEmbedding import FlagModel

        logger.info(
            f"Loading FlagModel from {path!r} with query_instruction_for_retrieval={self.query_instruction_for_retrieval!r}"
        )
        model = FlagModel(
            path,
            query_instruction_for_retrieval=self.query_instruction_for_retrieval,
            use_fp16=True,
        )
        return model

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
        result = self.model.encode(texts)
        return result.tolist()


@Vectorizer.register("bge_m3")
class LocalBGEM3Vectorizer(Vectorizer):
    """
    Invoke local bge-m3 embedding models to turn texts into embedding vectors.
    """

    # def __init__(self, config: Dict[str, Any]):
    #     super().__init__(config)
    def __init__(
        self,
        path: str,
        url: str = None,
        query_instruction_for_retrieval: str = None,
        vector_dimensions: int = None,
    ):
        super().__init__(vector_dimensions)
        self.url = url
        self.model_path = os.path.expanduser(path)
        config_path = os.path.join(self.model_path, "config.json")
        if not os.path.isfile(config_path):
            if url is None:
                message = f"model not found at {path!r}, nor model url specified"
                raise RuntimeError(message)
            self._download_model(path, url)
        if self.model_path in LOCAL_MODEL_MAP:
            logger.info("Found existing model, reuse.")
            model = LOCAL_MODEL_MAP[self.model_path]
        else:
            model = self._load_model(self.model_path)
            LOCAL_MODEL_MAP[self.model_path] = model
        self.model = model

    def _load_model(self, path):
        # We need to import sklearn at first, otherwise sklearn will fail on macOS with m chip.

        import sklearn  # noqa
        from FlagEmbedding import BGEM3FlagModel

        logger.info(f"Loading BGEM3FlagModel from {path!r}")
        model = BGEM3FlagModel(path, use_fp16=True)
        return model

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
        result = self.model.encode(texts)["dense_vecs"]
        return result.tolist()
