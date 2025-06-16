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
import json
from typing import Union, Iterable

import httpx

from kag.interface import SparseVectorizeModelABC, SparseEmbeddingVector
import logging

logger = logging.getLogger(__name__)


@SparseVectorizeModelABC.register("sparse_bge_m3")
class SparseBGEM3VectorizeModel(SparseVectorizeModelABC):
    """
    A class that extends the SparseVectorizeModelABC base class.
    It invokes sparse bge-m3 embedding services to convert texts into sparse embedding vectors.
    """

    def __init__(
        self,
        url: str,
        max_rate: float = 1000,
        time_period: float = 1,
        **kwargs,
    ):
        """
        Initializes the SparseBGEM3VectorizeModel instance.

        Args:
            url (str): The base URL for the sparse bge-m3 model service.
        """
        name = self.generate_key(url)
        super().__init__(name, max_rate, time_period)
        self.url = url

    @classmethod
    def generate_key(cls, url, *args, **kwargs) -> str:
        model = "sparse_bge_m3"
        return f"{cls}_{url}_{model}"

    @staticmethod
    def _get_headers():
        headers = {
            "Content-Type": "application/json",
            "MPS-app-name": "kag",
            "MPS-http-version": "1.0",
        }
        return headers

    @staticmethod
    def _make_request_data(texts):
        text_list = [texts] if isinstance(texts, str) else texts
        text_list = [text.strip()[:8000] for text in text_list]
        data = {"inputs": text_list, "return_sparse": True}
        features = {"data": data}
        json_data = {"features": features}
        return json_data

    @classmethod
    def _decode_sparse_vector(cls, value) -> SparseEmbeddingVector:
        result = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        return result

    @classmethod
    def _decode_response_data(cls, texts, response):
        res_map = response.json()
        result = res_map.get("resultMap").get("result")
        result_values = json.loads(result)
        result_vectors = [cls._decode_sparse_vector(val) for val in result_values]
        if isinstance(texts, str):
            return result_vectors[0]
        else:
            assert len(texts) == len(
                result_vectors
            ), f"Input size mismatch: {len(texts)} != {len(result_vectors)}"
            return result_vectors

    def vectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[SparseEmbeddingVector, Iterable[SparseEmbeddingVector]]:
        """
        Vectorizes a text string into a sparse embedding vector or multiple text strings
        into multiple sparse embedding vectors.

        Args:
            texts (Union[str, Iterable[str]]): The text or texts to vectorize.

        Returns:
            Union[SparseEmbeddingVector, Iterable[SparseEmbeddingVector]]: The sparse embedding vector(s) of the text(s).
        """
        headers = self._get_headers()
        json_data = self._make_request_data(texts)
        response = httpx.post(self.url, headers=headers, json=json_data)
        return self._decode_response_data(texts, response)

    async def avectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[SparseEmbeddingVector, Iterable[SparseEmbeddingVector]]:
        """
        Vectorizes a text string into s sparse embedding vector or multiple text strings
        into multiple sparse embedding vectors.

        Args:
            texts (Union[str, Iterable[str]]): The text or texts to vectorize.

        Returns:
            Union[SparseEmbeddingVector, Iterable[SparseEmbeddingVector]]: The sparse embedding vector(s) of the text(s).
        """
        headers = self._get_headers()
        json_data = self._make_request_data(texts)
        async with self.limiter:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.url, headers=headers, json=json_data)
        return self._decode_response_data(texts, response)
