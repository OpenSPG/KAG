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
)
from kag.interface.solver.model.schema_utils import SchemaUtils

logger = logging.getLogger()
chunk_cached_by_query_map = knext.common.cache.LinkCache(maxsize=100, ttl=300)


@RetrieverABC.register("table_retriever")
class TableRetriever(RetrieverABC):
    def __init__(
        self,
        vectorize_model: VectorizeModelABC = None,
        search_api: SearchApiABC = None,
        graph_api: GraphApiABC = None,
        top_k: int = 10,
        score_threshold=0.8,
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
        self.score_threshold = score_threshold

    def get_table(self, query, top_k) -> List[str]:
        topk_table_ids = {}
        query_vector = self.vectorize_model.vectorize(query)

        # recall top_k outline
        top_k_tables_from_name = self.search_api.search_vector(
            label=self.schema_helper.get_label_within_prefix("Table"),
            query_vector=query_vector,
            property_key="name",
            topk=top_k,
            ef_search=top_k * 3,
        )

        top_k_tables_from_content = self.search_api.search_vector(
            label=self.schema_helper.get_label_within_prefix("Table"),
            query_vector=query_vector,
            property_key="content",
            topk=top_k,
            ef_search=top_k * 3,
        )

        top_k_tables_from_beforeText = self.search_api.search_vector(
            label=self.schema_helper.get_label_within_prefix("Table"),
            query_vector=query_vector,
            property_key="beforeText",
            topk=top_k,
            ef_search=top_k * 3,
        )

        top_k_tables_from_afterText = self.search_api.search_vector(
            label=self.schema_helper.get_label_within_prefix("Table"),
            query_vector=query_vector,
            property_key="afterText",
            topk=top_k,
            ef_search=top_k * 3,
        )

        for item in (
            top_k_tables_from_name
            + top_k_tables_from_content
            + top_k_tables_from_beforeText
            + top_k_tables_from_afterText
        ):
            node_score = item.get("score", 0.0)
            if node_score >= self.score_threshold:
                key = item["node"]["id"]
                value = max(node_score, topk_table_ids.get(key, 0.0))
                topk_table_ids[key] = value

        return topk_table_ids

    def get_chunk_data(self, table_id, score=0.0):
        node = self.graph_api.get_entity_prop_by_id(
            label=self.schema_helper.get_label_within_prefix("Table"),
            biz_id=table_id,
        )
        node_dict = dict(node.items())

        before_text = node_dict["beforeText"]
        after_text = node_dict["afterText"]
        content = node_dict["content"].replace("_split_0", "")
        content = f"{before_text}\n{content}\n{after_text}"
        return ChunkData(
            content=content,
            title=node_dict["name"].replace("_split_0", ""),
            chunk_id=table_id,
            score=score,
        )

    def get_related_chunks(self, table_ids):
        chunks = []

        for table_id, score in table_ids.items():
            chunks.append(self.get_chunk_data(table_id, score=score))
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
                return RetrieverOutput(retriever_method=self.name)

            # recall table_ids through semantic vector
            topk_table_ids = self.get_table(query, top_k)

            # get table data for each table
            chunks = self.get_related_chunks(topk_table_ids)

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
        return {"name": "table_retriever"}
