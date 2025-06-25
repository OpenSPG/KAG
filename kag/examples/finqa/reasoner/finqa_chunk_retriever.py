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

import chromadb

import knext.common.cache
from kag.interface import PromptABC, VectorizeModelABC
from tenacity import retry, stop_after_attempt

from kag.interface import VectorizeModelABC as Vectorizer
from kag.interface import LLMClient
from typing import List, Dict, Optional

import numpy as np
import logging

from kag.solver.tools.graph_api.graph_api_abc import GraphApiABC
from kag.solver.tools.search_api.search_api_abc import SearchApiABC
from kag.solver.retriever.chunk_retriever import ChunkRetriever
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData, RelationData
from kag.solver.utils import init_prompt_with_fallback
from kag.solver.retriever.impl.default_chunk_retrieval import KAGRetriever
from kag.examples.finqa.reasoner.common import (
    _norm_doc,
)


logger = logging.getLogger(__name__)

ner_cache = knext.common.cache.LinkCache(maxsize=100, ttl=300)
query_sim_doc_cache = knext.common.cache.LinkCache(maxsize=100, ttl=300)


@ChunkRetriever.register("finqa_chunk_retriever")
class FinQAChunkRetriever(KAGRetriever):
    def __init__(
        self,
        ner_prompt: PromptABC = None,
        std_prompt: PromptABC = None,
        pagerank_threshold: float = 0.9,
        match_threshold: float = 0.9,
        pagerank_weight: float = 0.5,
        recall_num: int = 10,
        rerank_topk: int = 10,
        reranker_model_path: str = None,
        vectorize_model: VectorizeModelABC = None,
        graph_api: GraphApiABC = None,
        search_api: SearchApiABC = None,
        llm_client: LLMClient = None,
        **kwargs,
    ):
        super().__init__(
            ner_prompt,
            std_prompt,
            pagerank_threshold,
            match_threshold,
            pagerank_weight,
            recall_num,
            rerank_topk,
            reranker_model_path,
            vectorize_model,
            graph_api,
            search_api,
            llm_client,
            **kwargs,
        )
        self.rerank_docs_prompt = init_prompt_with_fallback(
            "rerank_chunks", self.biz_scene
        )

        current_dir = os.path.dirname(os.path.abspath(__file__))
        chromadb_path = os.path.join(current_dir, "..", "builder", "chunk_chromadb")
        os.makedirs(chromadb_path, exist_ok=True)
        chroma_client = chromadb.PersistentClient(path=chromadb_path)
        self.collection = chroma_client.create_collection(
            name="chunk", get_or_create=True
        )

    def rerank_docs(self, queries: List[str], passages: List[str]):
        return self._rerank_docs_by_llm(queries=queries, passages=passages)

    def recall_docs(
        self,
        queries: List[str],
        retrieved_spo: Optional[List[RelationData]] = None,
        **kwargs,
    ) -> List[str]:
        process_info = kwargs.get("kwargs", {}).get("process_info", None)
        file_name = process_info["file_name"]
        chunk_len = process_info["chunk_len"]
        query_txt = "\n".join(queries)
        rsts = self.collection.query(
            query_texts=[query_txt],
            n_results=20,
            where={"file_name": f"{file_name}_{chunk_len}"},
        )
        rst = sorted(rsts["documents"][0])
        rst = [f"#{file_name}#{c}#0.0" for c in rst]
        return rst

    @retry(stop=stop_after_attempt(3))
    def _rerank_docs_by_llm(self, queries: List[str], passages: List[str]):
        if len(passages) <= 1:
            return passages
        for_select_doc_list = list(passages)
        input_chunk_str = ""
        for i, doc in enumerate(for_select_doc_list):
            try:
                doc = _norm_doc(doc)
            except:
                pass
            input_chunk_str += f"\n### {i}\n{doc}\n"
        context = f"Parent Question:{queries[0]}"
        input_dict = {
            "question": str(queries[1:]),
            "chunks": input_chunk_str,
            "context": context,
        }
        best_chunk_index_list = self.llm_module.invoke(
            input_dict, self.rerank_docs_prompt, False, True
        )
        if best_chunk_index_list is None:
            logger.error("best_chunk_index is None")
            return []
        best_chunk_index_list = [
            b for b in best_chunk_index_list if b >= 0 and b < len(for_select_doc_list)
        ]
        best_chunks = [for_select_doc_list[b] for b in best_chunk_index_list]
        return best_chunks
