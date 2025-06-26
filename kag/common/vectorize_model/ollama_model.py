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
import asyncio
from typing import Union, Iterable, List

from ollama import AsyncClient

from kag.interface import VectorizeModelABC, EmbeddingVector
import logging

logger = logging.getLogger(__name__)


@VectorizeModelABC.register("Ollama")
@VectorizeModelABC.register("ollama")
class OllamaVectorizeModel(VectorizeModelABC):
    """
    A class that extends the VectorizeModelABC base class.
    It invokes Ollama embedding services to convert texts into embedding vectors.
    """

    def __init__(
        self,
        model: str = "bge-m3",
        base_url: str = "",
        vector_dimensions: int = None,
        timeout: float = None,
        max_rate: float = 1000,
        time_period: float = 1,
        batch_size: int = 8,
        **kwargs,
    ):
        """
        Initializes the OpenAIVectorizeModel instance.

        Args:
            model (str, optional): The model to use for embedding. Defaults to "text-embedding-3-small".
            api_key (str, optional): The API key for accessing the OpenAI service. Defaults to "".
            base_url (str, optional): The base URL for the OpenAI service. Defaults to "".
            vector_dimensions (int, optional): The number of dimensions for the embedding vectors. Defaults to None.
        """
        name = self.generate_key(base_url, model)
        super().__init__(name, vector_dimensions, max_rate, time_period)

        self.model = model
        self.timeout = timeout
        self.base_url = base_url
        self.batch_size = batch_size
        self.aclient = AsyncClient(host=self.base_url, timeout=self.timeout)

    @classmethod
    def generate_key(cls, base_url, model, *args, **kwargs) -> str:
        return f"{cls}_{base_url}_{model}"

    def vectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        return asyncio.run(self.avectorize(texts))

    async def avectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorize a text string into an embedding vector or multiple text strings into multiple embedding vectors.

        Args:
            texts (Union[str, Iterable[str]]): The text or texts to vectorize.

        Returns:
            Union[EmbeddingVector, Iterable[EmbeddingVector]]: The embedding vector(s) of the text(s).
        """

        # Handle empty strings in the input
        if isinstance(texts, list):
            # Create a set of original texts to remove empty and duplicated strings
            filtered_texts = [x for x in set(texts) if x]

            if not filtered_texts:
                return [[] for _ in texts]  # Return empty vectors for all inputs

            embeddings = await self._execute_batch_vectorize(filtered_texts)
            results = {
                text: embedding for text, embedding in zip(filtered_texts, embeddings)
            }

            return [results[text] if text else [] for text in texts]

        elif isinstance(texts, str) and not texts.strip():
            return []  # Return empty vector for empty string
        else:
            embeddings = await self._execute_batch_vectorize([texts])
            return embeddings[0]

    async def _execute_batch_vectorize(self, texts: List[str]) -> List[EmbeddingVector]:
        async def do_task_with_semaphore(_semaphore, _input: str) -> EmbeddingVector:
            async with _semaphore:
                embeddings_response = await self.aclient.embeddings(
                    prompt=_input, model=self.model
                )
            return embeddings_response.embedding

        try:
            semaphore = asyncio.Semaphore(self.batch_size)
            embeddings = await asyncio.gather(
                *[do_task_with_semaphore(semaphore, text) for text in texts]
            )
            return embeddings
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.error(f"input: {texts}")
            logger.error(f"model: {self.model}")
