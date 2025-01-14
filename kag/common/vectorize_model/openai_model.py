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

from typing import Union, Iterable
from openai import OpenAI, AzureOpenAI
from kag.interface import VectorizeModelABC, EmbeddingVector
from typing import Callable

@VectorizeModelABC.register("openai")
class OpenAIVectorizeModel(VectorizeModelABC):
    """
    A class that extends the VectorizeModelABC base class.
    It invokes OpenAI or OpenAI-compatible embedding services to convert texts into embedding vectors.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str = "",
        base_url: str = "",
        vector_dimensions: int = None,
        timeout: float = None,
    ):
        """
        Initializes the OpenAIVectorizeModel instance.

        Args:
            model (str, optional): The model to use for embedding. Defaults to "text-embedding-3-small".
            api_key (str, optional): The API key for accessing the OpenAI service. Defaults to "".
            base_url (str, optional): The base URL for the OpenAI service. Defaults to "".
            vector_dimensions (int, optional): The number of dimensions for the embedding vectors. Defaults to None.
        """
        super().__init__(vector_dimensions)
        self.model = model
        self.timeout = timeout
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def vectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorizes a text string into an embedding vector or multiple text strings into multiple embedding vectors.

        Args:
            texts (Union[str, Iterable[str]]): The text or texts to vectorize.

        Returns:
            Union[EmbeddingVector, Iterable[EmbeddingVector]]: The embedding vector(s) of the text(s).
        """
        results = self.client.embeddings.create(
            input=texts, model=self.model, timeout=self.timeout
        )
        results = [item.embedding for item in results.data]
        if isinstance(texts, str):
            assert len(results) == 1
            return results[0]
        else:
            assert len(results) == len(texts)
            return results

@VectorizeModelABC.register("azure_openai")
class AzureOpenAIVectorizeModel(VectorizeModelABC):
    ''' A class that extends the VectorizeModelABC base class.
    It invokes Azure OpenAI or Azure OpenAI-compatible embedding services to convert texts into embedding vectors.
    '''

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "text-embedding-ada-002",
        api_version: str = "2024-12-01-preview",
        vector_dimensions: int = None,
        timeout: float = None,
        azure_deployment: str = None,
        azure_ad_token: str = None,
        azure_ad_token_provider: Callable = None,
    ):
        """
        Initializes the AzureOpenAIVectorizeModel instance.

        Args:
            model (str, optional): The model to use for embedding. Defaults to "text-embedding-3-small".
            api_key (str, optional): The API key for accessing the Azure OpenAI service. Defaults to "".
            api_version (str): The API version for the Azure OpenAI API (eg. "2024-12-01-preview, 2024-10-01-preview,2024-05-01-preview").
            base_url (str, optional): The base URL for the Azure OpenAI service. Defaults to "".
            vector_dimensions (int, optional): The number of dimensions for the embedding vectors. Defaults to None.
            azure_ad_token: Your Azure Active Directory token, https://www.microsoft.com/en-us/security/business/identity-access/microsoft-entra-id
            azure_ad_token_provider: A function that returns an Azure Active Directory token, will be invoked on every request.
            azure_deployment: A model deployment, if given sets the base client URL to include `/deployments/{azure_deployment}`.
                Note: this means you won't be able to use non-deployment endpoints. Not supported with Assistants APIs.
        """
        super().__init__(vector_dimensions)
        self.model = model
        self.timeout = timeout
        self.client = AzureOpenAI(
            api_key=api_key,
            base_url=base_url,
            azure_deployment=azure_deployment,
            model=model,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            azure_ad_token_provider=azure_ad_token_provider,
        )

    def vectorize(
        self, texts: Union[str, Iterable[str]]
    ) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorizes a text string into an embedding vector or multiple text strings into multiple embedding vectors.

        Args:
            texts (Union[str, Iterable[str]]): The text or texts to vectorize.

        Returns:
            Union[EmbeddingVector, Iterable[EmbeddingVector]]: The embedding vector(s) of the text(s).
        """
        results = self.client.embeddings.create(
            input=texts, model=self.model, timeout=self.timeout
        )
        results = [item.embedding for item in results.data]
        if isinstance(texts, str):
            assert len(results) == 1
            return results[0]
        else:
            assert len(results) == len(texts)
            return results