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


class LocalBGEM3Vectorizer(Vectorizer):
    """
    Invoke local bge-m3 embedding models to turn texts into embedding vectors.
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
        self._path = path
        self._url = url
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
        from FlagEmbedding import BGEM3FlagModel

        print(f"Loading BGEM3FlagModel from {path!r}")
        model = BGEM3FlagModel(path, use_fp16=True)
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
        result = self._model.encode(texts)["dense_vecs"]
        return result.tolist()
