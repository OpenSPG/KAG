# -*- coding: utf-8 -*-
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
import os
import logging
import threading
import numpy as np
from typing import List
from kag.interface import RerankModelABC


LOCAL_MODEL_MAP = {}
logger = logging.getLogger()


@RerankModelABC.register("local_bge")
@RerankModelABC.register("local_bge_rerank_model")
class LocalBGERerankModel(RerankModelABC):
    """Local implementation of BGE rerank model with thread-safe loading.

    Extends RerankModelABC to provide GPU-based reranking using the FlagEmbedding library.
    Handles model downloading, caching, and concurrent access through thread locking.

    Attributes:
        model_path (str): Expanded user path to the model directory
        use_fp16 (bool): Flag to enable half-precision floating point computation
    """

    _LOCK = threading.Lock()

    def __init__(self, path: str, url: str = None, use_fp16: bool = True, **kwargs):
        """Initialize model with path/url fallback and thread-safe loading.

        Args:
            path (str): Local filesystem path to model directory
            url (str, optional): Download URL if model not found locally. Defaults to None.
            use_fp16 (bool, optional): Use FP16 precision if supported. Defaults to True.
            **kwargs: Additional parameters passed to parent class

        Raises:
            RuntimeError: If model not found and no download URL provided
        """
        name = kwargs.pop("name", None)
        if not name:
            name = "local_bge_rerank_model"
        super().__init__(name)

        self.model_path = os.path.expanduser(path)
        self.url = url
        if not os.path.exists(self.model_path):
            if not self.url:
                message = f"model not found at {path}, nor model url specified"
                raise RuntimeError(message)
            logger.info("Model file not found in path, start downloading...")
            self._download_model(self.model_path, self.url)

        self.model_path = self.default_implementation
        self.use_fp16 = use_fp16

        with LocalBGERerankModel._LOCK:
            if self.model_path in LOCAL_MODEL_MAP:
                logger.info("Found existing model, reuse.")
                model = LOCAL_MODEL_MAP[self.model_path]
            else:
                model = self._load_model(self.model_path, use_fp16)
                LOCAL_MODEL_MAP[self.model_path] = model
            self.model = model

    def _load_model(self, model_path, use_fp16):
        """Load FlagEmbedding reranker model with specified precision.

        Args:
            model_path (str): Path to model directory containing config.json
            use_fp16 (bool): Enable FP16 mode if GPU available

        Returns:
            FlagReranker: Initialized reranker model instance

        Raises:
            ImportError: If FlagEmbedding package not installed
            RuntimeError: If model fails to load
        """

        from FlagEmbedding import FlagReranker

        return FlagReranker(model_path, use_fp16=use_fp16)

    def compute_index(self, query: List[str], passages: List[str]):
        """Compute reranked passage indices using BGE model scores.

        Args:
            query (str): Search query string
            passages (List[str]): List of document passages to score

        Returns:
            List[int]: Passage indices sorted by descending relevance scores

        Raises:
            RuntimeError: If model inference fails
        """

        scores = self.model.compute_score([[query, x] for x in passages])
        sorted_idx = np.argsort(-np.array(scores))
        return sorted_idx
