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
import asyncio
from typing import List

import knext.common.cache
import logging

from kag.common.conf import KAG_PROJECT_CONF, KAG_CONFIG
from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
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

from knext.schema.client import CHUNK_TYPE

logger = logging.getLogger()
chunk_cached_by_query_map = knext.common.cache.LinkCache(maxsize=100, ttl=300)


@RetrieverABC.register("summary_chunk_retriever")
class SummaryChunkRetriever(RetrieverABC):
    def __init__(
        self,
        vectorize_model: VectorizeModelABC = None,
        search_api: SearchApiABC = None,
        graph_api: GraphApiABC = None,
        top_k: int = 10,
        score_threshold=0.85,
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

    async def _get_summaries(self, query, top_k) -> List[str]:
        topk_summary_ids = []
        query_vector = await self.vectorize_model.avectorize(query)

        # recall top_k summaries
        top_k_summaries = await asyncio.to_thread(
            lambda: self.search_api.search_vector(
                label=self.schema_helper.get_label_within_prefix("Summary"),
                property_key="content",
                query_vector=query_vector,
                topk=top_k,
            )
        )
        for item in top_k_summaries:
            topk_summary_ids.append(item["node"]["id"])

        return topk_summary_ids

    async def _get_children_summary_ids(self, summary_id) -> List[str]:
        entity = EntityData(
            entity_id=summary_id,
            node_type=self.schema_helper.get_label_within_prefix("Summary"),
        )
        oneHopGraphData = await asyncio.to_thread(
            lambda: self.graph_api.get_entity_one_hop(entity)
        )
        if not oneHopGraphData:
            return []
        if not oneHopGraphData.in_relations:
            return []
        children_summary_ids = set()
        for relationData in oneHopGraphData.in_relations.get("childOf", []):
            children_summary_ids.add(relationData.from_id)
        return list(children_summary_ids)

    """
        get children summaries of current summary
    """

    async def _get_children_summaries(self, summary_ids):
        tasks = []
        for summary_id in summary_ids:
            tasks.append(self._get_children_summary_ids(summary_id))
        results = await asyncio.gather(*tasks)
        children_summary_ids = set(item for result in results for item in result)
        return children_summary_ids

    async def _get_chunk_data(self, chunk_id, score=0.0):
        node = await asyncio.to_thread(
            lambda: self.graph_api.get_entity_prop_by_id(
                label=self.schema_helper.get_label_within_prefix(CHUNK_TYPE),
                biz_id=chunk_id,
            )
        )
        node_dict = dict(node.items())
        return ChunkData(
            content=node_dict["content"].replace("_split_0", ""),
            title=node_dict["name"].replace("_split_0", ""),
            chunk_id=chunk_id,
            score=score,
        )

    async def _get_related_chunk_ids(self, summary_id) -> List[str]:
        entity = EntityData(
            entity_id=summary_id,
            node_type=self.schema_helper.get_label_within_prefix("Summary"),
        )
        oneHopGraphData = await asyncio.to_thread(
            lambda: self.graph_api.get_entity_one_hop(entity)
        )

        # parse oneHopGraphData and get related chunks
        chunk_ids = set()
        for relationData in oneHopGraphData.out_relations.get("relateTo", []):
            chunk_ids.add(relationData.end_id)
        return list(chunk_ids)

    async def _get_related_chunks(self, summary_ids):
        tasks = []
        for summary_id in summary_ids:
            tasks.append(self._get_related_chunk_ids(summary_id))
        results = await asyncio.gather(*tasks)
        chunk_ids = set(item for result in results for item in result)

        tasks = []
        for chunk_id in chunk_ids:
            tasks.append(self._get_chunk_data(chunk_id))
        chunks = await asyncio.gather(*tasks)
        return chunks

    async def ainvoke(self, task, **kwargs) -> RetrieverOutput:
        query = task.arguments["query"]
        top_k = kwargs.get("top_k", self.top_k)
        try:
            cached = chunk_cached_by_query_map.get(query)
            if cached and len(cached.chunks) > top_k:
                return cached
            if not query:
                logger.error("chunk query is emtpy", exc_info=True)
                return RetrieverOutput()

            # recall summary through semantic vector
            topk_summary_ids = await self._get_summaries(query, top_k)

            # recall children summaries
            children_summary_ids = await self._get_children_summaries(topk_summary_ids)

            # get related chunk for each summary
            chunks = await self._get_related_chunks(
                topk_summary_ids + list(children_summary_ids)
            )

            # to retrieve output
            out = RetrieverOutput(chunks=chunks)
            chunk_cached_by_query_map.put(query, out)
            return out

        except Exception as e:
            logger.error(f"run calculate_sim_scores failed, info: {e}", exc_info=True)
            return RetrieverOutput()

    @property
    def input_indices(self):
        return ["Summary"]
