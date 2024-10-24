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
import sys
import tarfile
import threading
import requests
from typing import Any, Union, Iterable, Dict
from kag.common.vectorizer.vectorizer import Vectorizer

EmbeddingVector = Iterable[float]


class ContrieverVectorizer(Vectorizer):
    """
    Invoke local embedding models to turn texts into embedding vectors.
    """

    _local_model_map = {}
    _lock = threading.Lock()

    def __init__(self, config: Dict[str, Any]):
        import torch

        path = config.get("path")

        if path is None:
            message = "model path is required"
            raise RuntimeError(message)

        url = config.get("url", None)
        path = os.path.expanduser(path)
        config_path = os.path.join(path, "config.json")
        if not os.path.isfile(config_path):
            if url is None:
                message = f"model not found at {path!r}, nor model url specified"
                raise RuntimeError(message)
            self._download_model(path, url)
        if path not in sys.path:
            sys.path.insert(0, path)
        device = config.get("device")
        if device is None or device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        normalize = config.get("normalize", False)
        self._path = path
        self._url = url
        self._normalize = normalize
        self._device = device
        self._vector_dimensions = self._get_vector_dimensions(config)
        with self._lock:
            if path in self._local_model_map:
                self._model, self._tokenizer = self._local_model_map[path]
            else:
                self._model, self._tokenizer = self._load_model(path)
                self._local_model_map[path] = self._model, self._tokenizer

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

        from facebookresearch.contriever.src.contriever import Contriever
        from transformers import AutoTokenizer

        print(f"Loading facebook/contriever from {self._path!r} with normalize={self._normalize!r}")
        model = Contriever.from_pretrained(self._path).to(self._device)
        tokenizer = AutoTokenizer.from_pretrained(self._path)

        return model, tokenizer

    @property
    def vector_dimensions(self):
        """
        Dimension of generated embedding vectors.
        """
        if self._vector_dimensions is not None:
            return self._vector_dimensions
        return 768

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
        return_1d = False
        if isinstance(texts, str):
            texts = [texts]
            return_1d = True
        inputs = self._tokenizer(
            texts, padding=True, truncation=True, return_tensors="pt"
        ).to(self._device)
        embeddings = self._model(**inputs, normalize=self._normalize).detach().cpu().numpy().tolist()
        if return_1d:
            return embeddings[0]
        return embeddings
