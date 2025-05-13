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
import math
from typing import List, Dict
from kag.common.conf import KAG_PROJECT_CONF, KAG_CONFIG
from kag.interface import (
    RetrieverOutputMerger,
    LLMClient,
    VectorizeModelABC,
    PromptABC,
    RetrieverOutput,
)


def weightd_merge(
    chunk1: Dict[str, float], chunk2: Dict[str, float], alpha: float = 0.5
):
    def min_max_normalize(chunks):
        if len(chunks) == 0:
            return {}
        scores = chunks.values()
        max_score = max(scores)
        min_score = min(scores)
        ret_docs = {}
        for doc_id, score in chunks.items():
            if math.isclose(max_score, min_score, rel_tol=1e-9):
                score = 1
            else:
                score = (score - min_score) / (max_score - min_score)
            ret_docs[doc_id] = score
        return ret_docs

    chunk1 = min_max_normalize(chunk1)
    chunk2 = min_max_normalize(chunk2)

    merged = {}
    for doc_id, score in chunk1.items():
        if doc_id in merged:
            merged_score = merged[doc_id]
            merged_score += score * alpha
            merged[doc_id] = merged_score
        else:
            merged[doc_id] = score * alpha

    for doc_id, score in chunk2.items():
        if doc_id in merged:
            merged_score = merged[doc_id]
            merged_score += score * (1 - alpha)
            merged[doc_id] = merged_score
        else:
            merged[doc_id] = score * (1 - alpha)

    return merged


@RetrieverOutputMerger.register("kag_merger")
class KAGRetrieverOutputMerger(RetrieverOutputMerger):
    def __init__(
        self,
        top_k,
        llm: LLMClient = None,
        summary_prompt: PromptABC = None,
        vectorize_model: VectorizeModelABC = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.name = "kag_merger"
        self.top_k = top_k
        self.llm = llm
        from kag.builder.prompt.utils import init_prompt_with_fallback

        self.summary_prompt = summary_prompt or init_prompt_with_fallback(
            "thought_then_answer", KAG_PROJECT_CONF.biz_scene
        )

        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            KAG_CONFIG.all_config["vectorize_model"]
        )

    def invoke(
        self, query: str, retrieve_outputs: List[RetrieverOutput], **kwargs
    ) -> RetrieverOutput:
        return retrieve_outputs[0]
