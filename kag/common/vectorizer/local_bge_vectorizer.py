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
import threading
import tarfile
import requests
from typing import Any, Union, Iterable, Dict
from kag.common.vectorizer.vectorizer import Vectorizer


EmbeddingVector = Iterable[float]


class LocalBGEVectorizer(Vectorizer):
    """
    Invoke local bge embedding models to turn texts into embedding vectors.
    """

    _local_model_map = {}
    _lock = threading.Lock()

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        path = config.get("path")
        if path is None:
            message = "model path is required"
            raise RuntimeError(message)
        url = config.get("url")
        path = os.path.expanduser(path)
        config_path = os.path.join(path, "config.json")
        if not os.path.isfile(config_path):
            if url is None:
                message = f"model not found at {path!r}, nor model url specified"
                raise RuntimeError(message)
            self._download_model(path, url)
        default_chinese_query_instruction_for_retrieval = "为这个句子生成表示以用于向量检索："
        default_english_query_instruction_for_retrieval = "Represent this sentence for searching relevant passages:"
        if "BAAI/bge-base-zh-v1.5" in path:
            default_query_instruction_for_retrieval = default_chinese_query_instruction_for_retrieval
        else:
            default_query_instruction_for_retrieval = default_english_query_instruction_for_retrieval
        query_instruction_for_retrieval = config.get("query_instruction_for_retrieval", default_query_instruction_for_retrieval)
        self._path = path
        self._url = url
        self._query_instruction_for_retrieval = query_instruction_for_retrieval
        with self._lock:
            if path in self._local_model_map:
                self._model = self._local_model_map[path]
            else:
                self._model = self._load_model(path)
                self._local_model_map[path] = self._model

    @classmethod
    def _from_config(cls, config: Dict[str, Any]) -> Vectorizer:
        """
        Create vectorizer from `config`.

        :param config: vectorizer config
        :type config: Dict[str, Any]
        :return: vectorizer instance
        :rtype: Vectorizer
        """
        vectorizer = cls(config)
        return vectorizer

    def _download_model(self, path, url):
        res = requests.get(url)
        with io.BytesIO(res.content) as fileobj:
            with tarfile.open(fileobj=fileobj) as tar:
                tar.extractall(path=path)
        config_path = os.path.join(path, "config.json")
        if not os.path.isfile(config_path):
            message = f"model config not found at {config_path!r}, url {url!r} specified an invalid model"
            raise RuntimeError(message)

    def _load_model(self, path):
        # We need to import sklearn at first, otherwise sklearn will fail on macOS with m chip.
        import sklearn
        from FlagEmbedding import FlagModel

        print(f"Loading FlagModel from {path!r} with query_instruction_for_retrieval={self._query_instruction_for_retrieval!r}")
        model = FlagModel(path,
                          query_instruction_for_retrieval=self._query_instruction_for_retrieval,
                          use_fp16=True)
        return model

    def vectorize(self, texts: Union[str, Iterable[str]]) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorize a text string into an embedding vector or multiple text strings into
        multiple embedding vectors.

        :param texts: texts to vectorize
        :type texts: str or Iterable[str]
        :return: embedding vectors of the texts
        :rtype: EmbeddingVector or Iterable[EmbeddingVector]
        """
        result = self._model.encode(texts)
        return result.tolist()
