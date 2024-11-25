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
import json
import threading
import time
import sys
import tarfile
import requests
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Any, Union, Iterable, Dict

from kag.common.vectorizer.vectorizer import Vectorizer

EmbeddingVector = Iterable[float]


class MayaVectorizer(Vectorizer):
    """
    Invoke Maya embedding services to turn texts into embedding vectors.
    """

    def __init__(self, config: Dict[str, Any]):
        url = config.get("url")
        if url is None:
            message = "Maya model url is required"
            raise RuntimeError(message)
        debug_mode = config.get("debug_mode", True)
        truncation_length = config.get("truncation_length", 500)
        retry_times = config.get("retry_times", 3)
        retry_sleep_ms = config.get("retry_sleep_ms", 100.0)
        self._url = url
        self._debug_mode = str(debug_mode).lower().strip() == "true"
        self._truncation_length = truncation_length
        self._retry_times = retry_times
        self._retry_sleep_ms = retry_sleep_ms
        if not self._debug_mode:
            app_name = config.get("app_name")
            if app_name is None:
                message = "Maya app name is required"
                raise RuntimeError(message)
            app_token = config.get("app_token")
            if app_token is None:
                message = "Maya app token is required"
                raise RuntimeError(message)
            model_id = config.get("model_id")
            if model_id is None:
                message = "Maya model id is required"
                raise RuntimeError(message)
            model_version = config.get("model_version")
            if model_version is None:
                message = "Maya model version is required"
                raise RuntimeError(message)
            self._app_name = app_name
            self._app_token = app_token
            self._model_id = model_id
            self._model_version = model_version

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

    def _call_service(self, headers, data):
        res = requests.post(self._url, headers=headers, data=data)
        res.raise_for_status()
        body = res.json()
        success = body.get("success", False)
        if not success:
            message = "fail to invoke maya embedding model"
            if hasattr(self, "_model_id"):
                message += " %r" % self._model_id
            error_msg = body.get("errorMsg")
            if error_msg is not None:
                message += "; %s" % error_msg
            message += ". %s" % (body,)
            raise RuntimeError(message)
        if self._debug_mode:
            if self._is_corpus_bge_vectorizer:
                results = body["resultMap"]["res"]
            else:
                results = body["resultMap"]["result"]
            results = json.loads(results)
        else:
            results = body["embeddingList"]
        return results

    def _call_service_with_retry(self, headers, data):
        exception = None
        retry_count = 0
        while True:
            try:
                results = self._call_service(headers, data)
                return results
            except Exception as ex:
                exception = ex
            if retry_count >= self._retry_times:
                raise exception
            time.sleep((self._retry_sleep_ms * (1 << retry_count)) / 1000.0)
            retry_count += 1

    @property
    def _is_corpus_bge_vectorizer(self):
        return "corpus_bge_vectorizer" in self._url

    def _vectorize_batch(self, sentence_list, headers):
        trace_id = "knext.common.vectorizer.MayaVectorizer"
        if self._debug_mode:
            if self._is_corpus_bge_vectorizer:
                data = {"prompts": sentence_list}
            else:
                data = {"inputs": sentence_list, "trace_id": trace_id}
            data = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
            data = {"features": {"data": data}}
        else:
            data = {
                "appName": self._app_name,
                "appToken": self._app_token,
                "modelId": self._model_id,
                "modelVersion": self._model_version,
                "sentenceList": sentence_list,
                "traceId": trace_id,
                "invokeType": "embeddings",
            }
        data = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        data = data.encode("utf-8")
        results = self._call_service_with_retry(headers, data)
        return results

    def _vectorize_all(self, sentence_list):
        headers = {"Content-Type": "application/json"}
        if self._debug_mode:
            headers["MPS-app-name"] = "test"
            headers["MPS-http-version"] = "1.0"
        results = []
        batch_size = 32
        for i in range(0, len(sentence_list), batch_size):
            sentence_batch = sentence_list[i : i + batch_size]
            results += self._vectorize_batch(sentence_batch, headers)
        return results

    @property
    def vector_dimensions(self):
        """
        Dimension of generated embedding vectors.
        """
        return 768

    def vectorize(self, texts: Union[str, Iterable[str]]) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorize a text string into an embedding vector or multiple text strings into
        multiple embedding vectors.

        :param texts: texts to vectorize
        :type texts: str or Iterable[str]
        :return: embedding vectors of the texts
        :rtype: EmbeddingVector or Iterable[EmbeddingVector]
        """
        sentence_list = texts
        if isinstance(sentence_list, str):
            sentence_list = [sentence_list]
        sentence_list = [x[:self._truncation_length] for x in sentence_list]
        results = self._vectorize_all(sentence_list)
        if isinstance(texts, str):
            assert len(results) == 1
            return results[0]
        else:
            assert len(results) == len(texts)
            return results
