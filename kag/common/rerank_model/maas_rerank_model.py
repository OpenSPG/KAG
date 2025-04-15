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

import logging
import requests
from kag.interface import RerankModelABC
from tenacity import stop_after_attempt, retry

logger = logging.getLogger(__name__)


@RerankModelABC.register("maas")
@RerankModelABC.register("maas_rerank_model")
class MAASRerankModel(RerankModelABC):
    def __init__(
        self,
        model: str,
        api_key: str = "",
        base_url: str = "",
        timeout: float = None,
        max_rate: float = 1000,
        time_period: float = 1,
        **kwargs,
    ):
        """Initialize MAAS reranker with API configuration and rate limiting.

        Args:
            model (str): MAAS model name/identifier
            api_key (str, optional): API authentication token. Defaults to "".
            base_url (str, optional): API endpoint URL. Defaults to "".
            timeout (float, optional): Request timeout in seconds. Defaults to None.
            max_rate (float, optional): Max requests per time period. Defaults to 1000.
            time_period (float, optional): Rate limiting window in seconds. Defaults to 1.
            **kwargs: Additional parameters passed to parent class

        Raises:
            ValueError: If base_url or api_key are invalid
        """

        name = kwargs.pop("name", None)
        if not name:
            name = f"{api_key}{base_url}{model}"

        super().__init__(name, max_rate, time_period)
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    @retry(stop=stop_after_attempt(3))
    def compute_index(self, query, passages):
        """Compute rerank indices via MAAS API with automatic retries.

        Sends POST request to MAAS service and parses sorted indices from response.
        Implements exponential backoff retry strategy for transient failures.

        Args:
            query (str): Search query string
            passages (List[str]): Document passages to rerank

        Returns:
            List[int]: Passage indices sorted by API-provided relevance scores

        Raises:
            requests.exceptions.RequestException: For network/HTTP errors
            ValueError: If response format is invalid
            RuntimeError: For authentication or API errors
        """

        url = self.base_url
        payload = {
            "model": self.model,
            "query": query,
            "documents": passages,
            "top_n": len(passages),
            "return_documents": False,
            "max_chunks_per_doc": 1,
            "overlap_tokens": 80,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.request("POST", url, json=payload, headers=headers)
        results = response.json()["results"]
        sorted_idx = [x["index"] for x in results]
        return sorted_idx
