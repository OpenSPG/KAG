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
from kag.interface import (
    RetrieverABC,
    VectorizeModelABC,
    ChunkData,
    RetrieverOutput,
    EntityData,
    Context,
    LLMClient,
    PromptABC,
    Task,
)
from kag.interface.solver.model.schema_utils import SchemaUtils

from kag.common.config import LogicFormConfiguration
from kag.common.tools.search_api.search_api_abc import SearchApiABC
from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
from knext.schema.client import CHUNK_TYPE, TABLE_TYPE

logger = logging.getLogger()
chunk_cached_by_query_map = knext.common.cache.LinkCache(maxsize=100, ttl=300)


@RetrieverABC.register("atomic_query_chunk_retriever")
class AtomicQueryChunkRetriever(RetrieverABC):
    def __init__(
        self,
        vectorize_model: VectorizeModelABC = None,
        search_api: SearchApiABC = None,
        graph_api: GraphApiABC = None,
        llm_client: LLMClient = None,
        query_rewrite_prompt: PromptABC = None,
        top_k: int = 10,
        score_threshold=0.85,
        **kwargs,
    ):
        super().__init__(top_k, **kwargs)
        self.llm_client = llm_client
        self.query_rewrite_prompt = query_rewrite_prompt
        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            self.kag_config.all_config["vectorize_model"]
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
                    "KAG_PROJECT_ID": self.kag_project_config.project_id,
                    "KAG_PROJECT_HOST_ADDR": self.kag_project_config.host_addr,
                }
            )
        )
        self.score_threshold = score_threshold

    def recall_doc_by_atomic_query(self, atomic_query):
        entity = EntityData(
            entity_id=atomic_query["node"]["id"],
            node_type=self.schema_helper.get_label_within_prefix("AtomicQuery"),
        )
        subgraph = self.graph_api.get_entity_one_hop(entity)
        doc_id = subgraph.out_relations["sourceChunk"][0].end_id
        doc = self.graph_api.get_entity_prop_by_id(
            label=self.schema_helper.get_label_within_prefix(CHUNK_TYPE),
            biz_id=doc_id,
        )
        if doc == {}:
            doc = self.graph_api.get_entity_prop_by_id(
                label=self.schema_helper.get_label_within_prefix(TABLE_TYPE),
                biz_id=doc_id,
            )
        if doc == {}:
            doc = self.graph_api.get_entity_prop_by_id(
                label=self.schema_helper.get_label_within_prefix("Summary"),
                biz_id=doc_id,
            )

        if doc.get("content"):
            return ChunkData(
                content=doc["content"],
                title=doc["name"],
                chunk_id=doc["id"],
                score=atomic_query["score"],
            )
        else:
            return None

    def parse_chosen_atom_infos(self, context: Context):
        if not context:
            return []

        chunks = []
        for task in context.gen_task(False):
            if isinstance(task.result, RetrieverOutput):
                chunks.extend(task.result.chunks)
        return chunks

    def rewrite_query(self, query: str, context: Context):
        chosen_atom_infos = self.parse_chosen_atom_infos(context)
        i_decomposed, thinking, rewritten_queries = self.llm_client.invoke(
            {"content": query, "chosen_context": chosen_atom_infos},
            self.query_rewrite_prompt,
            with_except=False,
            with_json_parse=False,
        )

        rewritten_queries.append(query)
        if rewritten_queries is not None:
            return rewritten_queries
        else:
            rewritten_queries = []
            rewritten_queries.append(query)
            return rewritten_queries

    async def recall_atomic_query(self, query: str, context: Context):
        # rewrite query to expand diversity
        rewritten_queries = self.rewrite_query(query, context)
        # get vector for rewritten queries
        rewritten_queries_vector_list = await self.vectorize_model.avectorize(
            rewritten_queries
        )
        while rewritten_queries_vector_list is None:
            rewritten_queries_vector_list = await self.vectorize_model.avectorize(
                rewritten_queries
            )

        # recall atomic_query
        tasks = []
        if rewritten_queries_vector_list is not None:
            for rewritten_queries_vector in rewritten_queries_vector_list:
                task = asyncio.create_task(
                    asyncio.to_thread(
                        lambda: self.search_api.search_vector(
                            label=self.schema_helper.get_label_within_prefix(
                                "AtomicQuery"
                            ),
                            property_key="name",
                            query_vector=rewritten_queries_vector,
                            topk=self.top_k,
                            ef_search=self.top_k * 3,
                        )
                    )
                )
                tasks.append(task)
        else:
            tasks = []
        top_k_atomic_queries = await asyncio.gather(*tasks)

        top_k_atomic_queries_with_threshold = {}
        for top_k_atomic_query in top_k_atomic_queries:
            for atomic_query in top_k_atomic_query:
                score = atomic_query.get("score", 0.0)
                if score >= self.score_threshold:
                    atomic_id = atomic_query["node"]["id"]
                    if atomic_id not in top_k_atomic_queries_with_threshold:
                        top_k_atomic_queries_with_threshold[atomic_id] = atomic_query

                    max_score = max(
                        top_k_atomic_queries_with_threshold[atomic_id].get(
                            "score", 0.0
                        ),
                        score,
                    )
                    atomic_query["score"] = max_score
                    top_k_atomic_queries_with_threshold[atomic_id] = atomic_query

        res_list = []
        for item in top_k_atomic_queries_with_threshold.values():
            res_list.append(item)
        return res_list

    async def recall_sourceChunks_chunks(self, top_k_atomic_queries):
        tasks = []
        for item in top_k_atomic_queries:
            task = asyncio.create_task(
                asyncio.to_thread(lambda: self.recall_doc_by_atomic_query(item))
            )
            tasks.append(task)
        chunks = await asyncio.gather(*tasks)

        res_chunk_list = []
        chunk_id_set = set()
        for chunk in chunks:
            if chunk is None:
                continue
            if chunk.chunk_id not in chunk_id_set:
                chunk_id_set.add(chunk.chunk_id)
                res_chunk_list.append(chunk)

        return res_chunk_list

    @staticmethod
    def sync_wrapper(coro):
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    def invoke(self, task: Task, **kwargs) -> RetrieverOutput:
        query = task.arguments["query"]
        context = kwargs.get("context", None)
        try:
            if not query:
                logger.error("chunk query is emtpy", exc_info=True)
                return RetrieverOutput(retriever_method=self.name)

            # recall atomic queries
            top_k_atomic_queries = self.sync_wrapper(
                self.recall_atomic_query(query, context)
            )
            query_texts = [item["node"]["name"] for item in top_k_atomic_queries]
            query_text_related_chunks = []
            for query_text in query_texts:
                query_vector = self.vectorize_model.vectorize(query_text)
                top_k_docs = self.search_api.search_vector(
                    label=self.schema_helper.get_label_within_prefix(CHUNK_TYPE),
                    property_key="content",
                    query_vector=query_vector,
                    topk=self.top_k / 2,
                    ef_search=self.top_k / 2 * 3,
                )
                query_text_related_chunks.extend(top_k_docs)

            query_text_related_chunks = [
                ChunkData(
                    content=item["node"]["content"],
                    title=item["node"]["name"],
                    chunk_id=item["node"]["id"],
                    score=item["score"],
                )
                for item in query_text_related_chunks
            ]

            # recall atomic_relatedTo_chunks
            chunks = self.sync_wrapper(
                self.recall_sourceChunks_chunks(top_k_atomic_queries)
            )

            chunks = chunks + query_text_related_chunks

            out = RetrieverOutput(retriever_method=self.name, chunks=chunks)
            return out
        except Exception as e:
            logger.error(f"run calculate_sim_scores failed, info: {e}", exc_info=True)
            return RetrieverOutput(retriever_method=self.name, err_msg=str(e))

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
