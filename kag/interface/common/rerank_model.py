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
import tarfile
import numpy as np
import requests
import logging
import asyncio

from kag.common.rate_limiter import RATE_LIMITER_MANGER
from kag.common.registry import Registrable
from typing import List

logger = logging.getLogger()


@Registrable.register("rerank_model")
class RerankModelABC(Registrable):
    """Abstract base class for reranking models with rate limiting capabilities.

    This class provides core functionality for model downloading and reranking
    operations, including rate limiting and error handling for index computation.

    Args:
        name (str): Identifier for the rate limiter
        max_rate (float, optional): Maximum allowed requests per time period. Defaults to 1000.
        time_period (float, optional): Time window for rate limiting in seconds. Defaults to 1.
    """

    def __init__(
        self,
        name: str,
        max_rate: float = 1000,
        time_period: float = 1,
    ):
        self.limiter = RATE_LIMITER_MANGER.get_rate_limiter(name, max_rate, time_period)

    def _download_model(self, path, url):
        """Downloads and extracts a model archive from the specified URL.

        Verifies the presence of a valid config.json file in the extracted contents.
        Uses streaming download with in-memory extraction to minimize disk usage.

        Args:
            path (str): Destination directory path for extraction
            url (str): Source URL of the model archive

        Raises:
            RuntimeError: If config.json is missing in the extracted contents
        """
        logger.info(f"download model from:\n{url} to:\n{path}")
        res = requests.get(url)
        with io.BytesIO(res.content) as fileobj:
            with tarfile.open(fileobj=fileobj) as tar:
                tar.extractall(path=path)
        config_path = os.path.join(path, "config.json")
        if not os.path.isfile(config_path):
            message = f"model config not found at {config_path!r}, url {url!r} specified an invalid model"
            raise RuntimeError(message)

    def compute_index(self, query: str, passages: List[str]):
        """Abstract method to compute reranked passage indices for a query.

        Must be implemented by subclasses to provide the actual reranking logic.

        Args:
            query (str): Search query string
            passages (List[str]): List of document passages to rerank

        Returns:
            List[int]: Reranked passage indices in descending relevance order

        Raises:
            NotImplementedError: If not overridden by subclasses
        """
        message = "abstract method compute_index is not implemented"
        raise NotImplementedError(message)

    def rerank(self, queries: List[str], passages: List[str]):
        """Performs multi-query reranking of passages with error recovery.

        Combines reranking results from multiple queries using reciprocal rank fusion.
        Handles compute_index failures by falling back to original rankings.

        Args:
            queries (List[str]): Multiple query strings for reranking
            passages (List[str]): List of passages to rerank

        Returns:
            List[str]: Reranked passages in descending order of combined scores
        """
        rank_scores = np.array([1 / (1 + i) for i in range(len(passages))])
        passage_scores = np.zeros(len(passages)) + rank_scores
        for query in queries:
            try:
                sorted_idx = self.compute_index(query, passages)
            except Exception as e:
                import traceback

                traceback.print_exc()
                logger.warning(
                    f"failed to compute reranked index, fallback to origin rank, info: {e}"
                )
                sorted_idx = list(range(len(passages)))
            for rank, passage_id in enumerate(sorted_idx):
                passage_scores[passage_id] += rank_scores[rank]

        merged_sorted_idx = np.argsort(-passage_scores)
        new_passages = [passages[x] for x in merged_sorted_idx]
        return new_passages

    async def arerank(self, queries: List[str], passages: List[str]):
        """Asynchronous version of rerank with rate limiting.

        Uses async rate limiting and runs the rerank operation in a threadpool.

        Args:
            queries (List[str]): Multiple query strings for reranking
            passages (List[str]): List of passages to rerank

        Returns:
            List[str]: Reranked passages in descending order of combined scores
        """
        async with self.limiter:
            return await asyncio.to_thread(lambda: self.rerank(queries, passages))
