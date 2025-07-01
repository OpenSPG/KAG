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
import logging
from typing import List

import knext.common.cache
from kag.common.config import LogicFormConfiguration
from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
from kag.common.tools.search_api.search_api_abc import SearchApiABC
from kag.interface import (
    RetrieverABC,
    VectorizeModelABC,
    ChunkData,
    RetrieverOutput,
    EntityData,
)
from kag.interface.solver.model.schema_utils import SchemaUtils
from knext.schema.client import CHUNK_TYPE

logger = logging.getLogger()
chunk_cached_by_query_map = knext.common.cache.LinkCache(maxsize=100, ttl=300)


@RetrieverABC.register("outline_chunk_retriever")
class OutlineChunkRetriever(RetrieverABC):
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

    def get_outlines(self, query, top_k) -> List[str]:
        topk_outline_ids = []
        query_vector = self.vectorize_model.vectorize(query)

        # recall top_k outline
        top_k_outlines = self.search_api.search_vector(
            label=self.schema_helper.get_label_within_prefix("Outline"),
            property_key="name",
            query_vector=query_vector,
            topk=top_k,
            ef_search=top_k * 3,
        )
        for item in top_k_outlines:
            topk_outline_ids.append(item["node"]["id"])

        return topk_outline_ids

    """
        get children outline of current outline
    """

    def get_children_outlines(self, outline_ids):
        children_outline_ids = set()
        for outline_id in outline_ids:
            entity = EntityData(
                entity_id=outline_id,
                node_type=self.schema_helper.get_label_within_prefix("Outline"),
            )
            oneHopGraphData = self.graph_api.get_entity_one_hop(entity)
            if not oneHopGraphData:
                continue
            if not oneHopGraphData.in_relations:
                continue
            # parse oneHopGraphData and get children outline

            for relationData in oneHopGraphData.in_relations.get("childOf", []):
                children_outline_ids.add(relationData.from_id)
        return children_outline_ids

    def get_chunk_data(self, chunk_id, score=0.0):
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

    def get_related_chunks(self, outline_ids):
        chunks = []
        chunk_ids = set()
        for outline_id in outline_ids:
            entity = EntityData(
                entity_id=outline_id,
                node_type=self.schema_helper.get_label_within_prefix("Outline"),
            )
            oneHopGraphData = self.graph_api.get_entity_one_hop(entity)

            # parse oneHopGraphData and get related chunks
            for relationData in oneHopGraphData.out_relations.get("sourceChunk", []):
                chunk_ids.add(relationData.end_id)

        for chunk_id in chunk_ids:
            chunks.append(self.get_chunk_data(chunk_id))
        return chunks

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
                    err_msg="chunk query is empty",
                )

            # recall outline through semantic vector
            topk_outline_ids = self.get_outlines(query, top_k)

            # recall children outlines
            children_outline_ids = self.get_children_outlines(topk_outline_ids)

            # get related chunk for each outline
            chunks = self.get_related_chunks(
                topk_outline_ids + list(children_outline_ids)
            )

            # to retrieve output
            out = RetrieverOutput(retriever_method=self.name, chunks=chunks)
            chunk_cached_by_query_map.put(query, out)
            return out

        except Exception as e:
            logger.error(f"run calculate_sim_scores failed, info: {e}", exc_info=True)
            return RetrieverOutput(retriever_method=self.name, err_msg=str(e))

    @property
    def input_indices(self):
        return ["Outline"]

    def schema(self):
        return {"name": "outline_chunk_retriever"}
