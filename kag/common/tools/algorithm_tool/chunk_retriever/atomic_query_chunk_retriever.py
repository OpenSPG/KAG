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
import asyncio
from kag.common.conf import KAG_PROJECT_CONF, KAG_CONFIG
from kag.interface import (
    RetrieverABC,
    VectorizeModelABC,
    ChunkData,
    RetrieverOutput,
    EntityData,
)
from kag.interface.solver.model.schema_utils import SchemaUtils

from kag.common.config import LogicFormConfiguration
from kag.common.tools.search_api.search_api_abc import SearchApiABC
from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
from knext.schema.client import CHUNK_TYPE

logger = logging.getLogger()
chunk_cached_by_query_map = knext.common.cache.LinkCache(maxsize=100, ttl=300)


@RetrieverABC.register("atomic_query_chunk_retriever")
class AtomicQueryChunkRetriever(RetrieverABC):
    def __init__(
        self,
        vectorize_model: VectorizeModelABC = None,
        search_api: SearchApiABC = None,
        graph_api: GraphApiABC = None,
        top_k: int = 10,
        **kwargs,
    ):
        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            KAG_CONFIG.all_config["vectorize_model"]
        )
        self.search_api = search_api or SearchApiABC.from_config(
            {"type": "openspg_search_api"}
        )
        self.graph_api = graph_api or GraphApiABC.from_config(
            {"type": "openspg_graph_api"}
        )

        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
                }
            )
        )
        super().__init__(top_k, **kwargs)

    def extract_doc_by_atomic_query(self, atomic_query):
        entity = EntityData(
            entity_id=atomic_query["node"]["id"],
            node_type=self.schema_helper.get_label_within_prefix("AtomicQuery"),
        )
        subgraph = self.graph_api.get_entity_one_hop(entity)
        doc_id = subgraph.out_relations["relateTo"][0].end_id
        doc = self.graph_api.get_entity_prop_by_id(
            label=self.schema_helper.get_label_within_prefix(CHUNK_TYPE),
            biz_id=doc_id,
        )

        return ChunkData(
            content=doc["content"],
            title=doc["name"],
            chunk_id=doc["id"],
            score=atomic_query["score"],
        )

    async def ainvoke(self, task, **kwargs) -> RetrieverOutput:
        query = task.arguments["query"]
        top_k = kwargs.get("top_k", self.top_k)
        try:
            if not query:
                logger.error("chunk query is emtpy", exc_info=True)
                return RetrieverOutput(retriever_method=self.schema().get("name", ""))
            query_vector = await self.vectorize_model.avectorize(query)
            top_k_atomic_queries = await asyncio.to_thread(
                lambda: self.search_api.search_vector(
                    label=self.schema_helper.get_label_within_prefix("AtomicQuery"),
                    property_key="content",
                    query_vector=query_vector,
                    topk=top_k,
                )
            )

            chunks = []
            tasks = []
            for item in top_k_atomic_queries:
                task = asyncio.create_task(
                    asyncio.to_thread(lambda: self.extract_doc_by_atomic_query(item))
                )
                tasks.append(task)
            chunks = await asyncio.gather(*tasks)
            out = RetrieverOutput(chunks=chunks, retriever_method=self.schema().get("name", ""))
            return out

        except Exception as e:
            logger.error(f"run calculate_sim_scores failed, info: {e}", exc_info=True)
            return RetrieverOutput(retriever_method=self.schema().get("name", ""))

    def schema(self):
        return {
            "name": "atomic_query_based_chunk_retriever",
            "description": "Retrieve relevant text chunks from document store using atomic query similarity search",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for retrieving relevant text chunks",
                    },
                },
                "required": ["query"],
            },
        }

    @property
    def input_indices(self):
        return ["atomic_query"]
