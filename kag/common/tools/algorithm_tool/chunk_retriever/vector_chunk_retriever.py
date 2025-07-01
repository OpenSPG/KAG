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

import knext.common.cache
import logging

from kag.interface import RetrieverABC, VectorizeModelABC, ChunkData, RetrieverOutput
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.config import LogicFormConfiguration
from kag.common.tools.search_api.search_api_abc import SearchApiABC

from knext.schema.client import CHUNK_TYPE

logger = logging.getLogger()
chunk_cached_by_query_map = knext.common.cache.LinkCache(maxsize=100, ttl=300)


@RetrieverABC.register("vector_chunk_retriever")
class VectorChunkRetriever(RetrieverABC):
    def __init__(
        self,
        vectorize_model: VectorizeModelABC = None,
        search_api: SearchApiABC = None,
        top_k: int = 10,
        score_threshold=0.85,
        **kwargs,
    ):
        super().__init__(top_k, **kwargs)
        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            self.kag_config.all_config["vectorize_model"]
        )
        self.search_api = search_api or SearchApiABC.from_config(
            {"type": "openspg_search_api"}
        )
        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": self.kag_project_config.project_id,
                    "KAG_PROJECT_HOST_ADDR": self.kag_project_config.host_addr,
                }
            )
        )
        self.score_threshold = score_threshold

    def invoke(self, task, **kwargs) -> RetrieverOutput:
        query = task.arguments["query"]
        top_k = kwargs.get("top_k", self.top_k)
        try:
            cached = chunk_cached_by_query_map.get(query)
            if cached and len(cached.chunks) > top_k:
                return cached
            if not query:
                logger.error("chunk query is emtpy", exc_info=True)
                return RetrieverOutput(
                    retriever_method=self.name,
                    err_msg="query is empty",
                )
            query_vector = self.vectorize_model.vectorize(query)
            top_k_docs = self.search_api.search_vector(
                label=self.schema_helper.get_label_within_prefix(CHUNK_TYPE),
                property_key="content",
                query_vector=query_vector,
                topk=top_k,
                ef_search=top_k * 7,
            )
            top_k_docs_name = self.search_api.search_vector(
                label=self.schema_helper.get_label_within_prefix(CHUNK_TYPE),
                property_key="name",
                query_vector=query_vector,
                topk=top_k / 2,
                ef_search=top_k / 2 * 3,
            )
            top_k_docs = top_k_docs_name + top_k_docs

            merged = {}
            chunk_map = {}
            chunks = []
            for item in top_k_docs:
                score = item.get("score", 0.0)
                if score >= self.score_threshold:
                    chunk = ChunkData(
                        content=item["node"].get("content", ""),
                        title=item["node"]["name"],
                        chunk_id=item["node"]["id"],
                        score=score,
                    )
                    if chunk.chunk_id not in merged:
                        merged[chunk.chunk_id] = score
                    if merged[chunk.chunk_id] < score:
                        merged[chunk.chunk_id] = score
                    chunk_map[chunk.chunk_id] = chunk

            sorted_chunk_ids = sorted(merged.items(), key=lambda x: -x[1])
            for item in sorted_chunk_ids:
                chunk_id, score = item
                chunk = chunk_map[chunk_id]
                chunks.append(
                    ChunkData(
                        content=chunk.content,
                        title=chunk.title,
                        chunk_id=chunk.chunk_id,
                        score=score,
                    )
                )
            out = RetrieverOutput(chunks=chunks, retriever_method=self.name)
            chunk_cached_by_query_map.put(query, out)
            return out

        except Exception as e:
            logger.error(f"run calculate_sim_scores failed, info: {e}", exc_info=True)
            return RetrieverOutput(retriever_method=self.name, err_msg=str(e))

    def schema(self):
        return {
            "name": "vector_chunk_retriever",
            "description": "Retrieve relevant text chunks from document store using vector similarity search",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for retrieving relevant text chunks",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        }

    @property
    def input_indices(self):
        return ["chunk"]
