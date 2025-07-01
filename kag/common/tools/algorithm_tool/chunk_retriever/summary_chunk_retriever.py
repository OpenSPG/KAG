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
from typing import List

import knext.common.cache
import logging

from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
from kag.interface import (
    RetrieverABC,
    VectorizeModelABC,
    ChunkData,
    RetrieverOutput,
    EntityData,
    Task,
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
        super().__init__(top_k, **kwargs)
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

    def _get_summaries(self, query, top_k) -> List[str]:
        topk_summary_ids = []
        query_vector = self.vectorize_model.vectorize(query)

        # recall top_k summaries
        top_k_summaries = self.search_api.search_vector(
            label=self.schema_helper.get_label_within_prefix("Summary"),
            property_key="content",
            query_vector=query_vector,
            topk=top_k,
            ef_search=top_k * 3,
        )
        for item in top_k_summaries:
            topk_summary_ids.append(item["node"]["id"])

        return topk_summary_ids

    def _get_children_summary_ids(self, summary_id) -> List[str]:
        entity = EntityData(
            entity_id=summary_id,
            node_type=self.schema_helper.get_label_within_prefix("Summary"),
        )
        oneHopGraphData = self.graph_api.get_entity_one_hop(entity)
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

    def _get_children_summaries(self, summary_ids):
        results = []
        for summary_id in summary_ids:
            results.append(self._get_children_summary_ids(summary_id))
        children_summary_ids = set(item for result in results for item in result)
        return children_summary_ids

    def _get_chunk_data(self, chunk_id, score=0.0):
        node = self.graph_api.get_entity_prop_by_id(
            label=self.schema_helper.get_label_within_prefix(CHUNK_TYPE),
            biz_id=chunk_id,
        )
        node_dict = dict(node.items())
        return ChunkData(
            content=node_dict.get("content", "").replace("_split_0", ""),
            title=node_dict.get("name", "").replace("_split_0", ""),
            chunk_id=chunk_id,
            score=score,
        )

    def _get_related_chunk_ids(self, summary_id) -> List[str]:
        entity = EntityData(
            entity_id=summary_id,
            node_type=self.schema_helper.get_label_within_prefix("Summary"),
        )
        oneHopGraphData = self.graph_api.get_entity_one_hop(entity)

        # parse oneHopGraphData and get related chunks
        chunk_ids = set()
        for relationData in oneHopGraphData.out_relations.get("sourceChunk", []):
            chunk_ids.add(relationData.end_id)
        # return list(chunk_ids)

        # chunk_id 和summary_id 一致，先暂时返回summary_id
        return [summary_id]

    def _get_related_chunks(self, summary_ids):
        results = []
        for summary_id in summary_ids:
            results.append(self._get_related_chunk_ids(summary_id))
        chunk_ids = set(item for result in results for item in result)

        chunks = []
        for chunk_id in chunk_ids:
            chunks.append(self._get_chunk_data(chunk_id))
        return chunks

    def invoke(self, task: Task, **kwargs) -> RetrieverOutput:
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

            # recall summary through semantic vector
            topk_summary_ids = self._get_summaries(query, top_k)

            # recall children summaries
            children_summary_ids = self._get_children_summaries(topk_summary_ids)

            # get related chunk for each summary
            chunks = self._get_related_chunks(
                topk_summary_ids + list(children_summary_ids)
            )

            # to retrieve output
            out = RetrieverOutput(chunks=chunks, retriever_method=self.name)
            chunk_cached_by_query_map.put(query, out)
            return out

        except Exception as e:
            logger.error(f"run calculate_sim_scores failed, info: {e}", exc_info=True)
            return RetrieverOutput(retriever_method=self.name, err_msg=str(e))

    @property
    def input_indices(self):
        return ["Summary"]

    def schema(self):
        return {"name": "summary_chunk_retriever"}
