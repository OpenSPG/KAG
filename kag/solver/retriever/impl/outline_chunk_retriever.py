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
from collections import deque
from typing import List, Optional

import numpy as np

from kag.common.conf import KAG_CONFIG
from kag.interface import VectorizeModelABC, LLMClient
from kag.solver.logic.core_modules.common.one_hop_graph import RelationData, EntityData
from kag.solver.logic.core_modules.common.text_sim_by_vector import cosine_similarity
from kag.solver.retriever.chunk_retriever import ChunkRetriever
from kag.solver.tools.graph_api.graph_api_abc import GraphApiABC
from kag.solver.tools.search_api.search_api_abc import SearchApiABC
from knext.schema.client import CHUNK_TYPE, TITLE_TYPE


@ChunkRetriever.register("outline_chunk_retriever")
class OutlineChunkRetriever(ChunkRetriever):
    def __init__(
        self,
        recall_num: int = 10,
        rerank_topk: int = 10,
        vectorize_model: VectorizeModelABC = None,
        graph_api: GraphApiABC = None,
        search_api: SearchApiABC = None,
        llm_client: LLMClient = None,
        **kwargs,
    ):
        super().__init__(
            recall_num, rerank_topk, graph_api, search_api, llm_client, **kwargs
        )
        if vectorize_model is None:
            vectorize_model = VectorizeModelABC.from_config(
                KAG_CONFIG.all_config["vectorize_model"]
            )
        self.vectorize_model = vectorize_model

    def recall_docs(
        self,
        queries: List[str],
        retrieved_spo: Optional[List[RelationData]] = None,
        **kwargs
    ) -> List[str]:
        """
        Recalls documents based on the given query.

        Parameters:
            queries (list of str): The queries string to search for.
            retrieved_spo (Optional[List[RelationData]], optional): A list of previously retrieved relation data. Defaults to None.
            **kwargs: Additional keyword arguments for retrieval.

        Returns:
            List[str]: A list of recalled document IDs or content.
        """
        if not queries:
            return []
        if self.recall_num == 0:
            return []
        chunk_ids = set()
        title_ids = set()
        primary_query_vector = None
        for query in queries:
            query_vector = self.vectorize_model.vectorize(query)
            if primary_query_vector is None:
                primary_query_vector = query_vector
            query_chunk_ids = self._search_chunks(query_vector, chunk_nums=self.recall_num * 20)
            chunk_ids.update(query_chunk_ids)
            query_title_ids = self._search_titles(query_vector, title_nums=self.recall_num)
            title_ids.update(query_title_ids)
        descendant_title_ids = self._get_all_descendant_titles(title_ids)
        for descendant_title_id in descendant_title_ids:
            descendant_chunk_ids = self._get_direct_owned_chunks(descendant_title_id)
            chunk_ids.update(descendant_chunk_ids)
        chunk_nodes = self._get_chunk_nodes(chunk_ids)
        self._compute_chunk_similarity(chunk_nodes, primary_query_vector)
        chunk_nodes.sort(key=lambda x: x[1], reverse=True)
        del chunk_nodes[self.recall_num:]
        chunks = [f'#{item["name"]}#{item["content"]}#{score}' for item, score in chunk_nodes]
        return chunks

    def _search_chunks(self, query_vector, chunk_nums):
        top_k = self.search_api.search_vector(
            label=self.schema.get_label_within_prefix(CHUNK_TYPE),
            property_key="content",
            query_vector=query_vector,
            topk=chunk_nums,
        )
        chunk_ids = [item["node"]["id"] for item in top_k]
        return chunk_ids

    def _search_titles(self, query_vector, title_nums):
        top_k = self.search_api.search_vector(
            label=self.schema.get_label_within_prefix(TITLE_TYPE),
            property_key="name",
            query_vector=query_vector,
            topk=title_nums,
        )
        title_ids = [item["node"]["id"] for item in top_k]
        return title_ids

    def _get_all_descendant_titles(self, title_ids):
        result = set(title_ids)
        queue = deque(title_ids)
        while queue:
            title_id = queue.popleft()
            children = self._get_direct_child_titles(title_id)
            for child in children:
                if child not in result:
                    result.add(child)
                    queue.append(child)
        return result

    def _get_direct_child_titles(self, title_id):
        start = EntityData()
        start.biz_id = title_id
        start.type = self.schema.get_label_within_prefix(TITLE_TYPE)
        one_hop_data = self.graph_api.get_entity_one_hop(start)
        if "hasChild" not in one_hop_data.out_relations:
            return set()
        child_titles = set()
        for relation in one_hop_data.out_relations["hasChild"]:
            child_titles.add(relation.end_id)
        return child_titles

    def _get_direct_owned_chunks(self, title_id):
        start = EntityData()
        start.biz_id = title_id
        start.type = self.schema.get_label_within_prefix(TITLE_TYPE)
        one_hop_data = self.graph_api.get_entity_one_hop(start)
        if "hasContent" not in one_hop_data.out_relations:
            return set()
        child_titles = set()
        for relation in one_hop_data.out_relations["hasContent"]:
            child_titles.add(relation.end_id)
        return child_titles

    def _get_chunk_nodes(self, chunk_ids):
        nodes = []
        label = self.schema.get_label_within_prefix(CHUNK_TYPE)
        for chunk_id in chunk_ids:
            node = self.graph_api.get_entity_prop_by_id(chunk_id, label)
            nodes.append(node)
        return nodes

    def _compute_chunk_similarity(self, chunk_nodes, query_vector):
        query_vector = np.array(query_vector)
        for i, chunk_node in enumerate(chunk_nodes):
            cosine = self._compute_vector_similarity(chunk_node, query_vector)
            score = (1.0 + cosine.item()) / 2.0
            chunk_nodes[i] = chunk_node, score

    def _compute_vector_similarity(self, chunk_node, query_vector):
        content_vector = chunk_node["_content_vector"]
        content_vector = np.array(content_vector)
        cosine = cosine_similarity(content_vector, query_vector)
        return cosine
