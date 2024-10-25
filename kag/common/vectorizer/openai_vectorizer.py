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

from typing import Any, Union, Iterable, Dict
from openai import OpenAI
from kag.common.vectorizer.vectorizer import Vectorizer


EmbeddingVector = Iterable[float]


class OpenAIVectorizer(Vectorizer):
    """
    Invoke OpenAI or OpenAI-compatible embedding services to turn texts into embedding vectors.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = config.get("model","text-embedding-3-small")
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        if not self.api_key:
            raise ValueError("OpenAI API key is not set")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

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

    def vectorize(self, texts: Union[str, Iterable[str]]) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorize a text string into an embedding vector or multiple text strings into
        multiple embedding vectors.

        :param texts: texts to vectorize
        :type texts: str or Iterable[str]
        :return: embedding vectors of the texts
        :rtype: EmbeddingVector or Iterable[EmbeddingVector]
        """
        results = self.client.embeddings.create(input=texts, model=self.model)
        results = [item.embedding for item in results.data]
        if isinstance(texts, str):
            assert len(results) == 1
            return results[0]
        else:
            assert len(results) == len(texts)
            return results
