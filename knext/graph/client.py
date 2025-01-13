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

from typing import List, Dict

from knext.common.base.client import Client
from knext.common.rest import ApiClient, Configuration
from knext.graph import (
    rest,
    GetPageRankScoresRequest,
    GetPageRankScoresRequestStartNodes,
    WriterGraphRequest,
    QueryVertexRequest,
    ExpendOneHopRequest,
    EdgeTypeName,
)


class GraphClient(Client):
    """ """

    def __init__(self, host_addr: str = None, project_id: int = None):
        super().__init__(host_addr, project_id)
        self._rest_client: rest.GraphApi = rest.GraphApi(
            api_client=ApiClient(configuration=Configuration(host=host_addr))
        )

    def calculate_pagerank_scores(self, target_vertex_type, start_nodes: List[Dict]):
        """
        Calculate and retrieve PageRank scores for the given starting nodes.

        Parameters:
        target_vertex_type (str): Return target vectex type ppr score
        start_nodes (list): A list containing document fragment IDs to be used as starting nodes for the PageRank algorithm.

        Returns:
        ppr_doc_scores (dict): A dictionary containing each document fragment ID and its corresponding PageRank score.

        This method uses the PageRank algorithm in the graph store to compute scores for document fragments. If `start_nodes` is empty,
        it returns an empty dictionary. Otherwise, it attempts to retrieve PageRank scores from the graph store and converts the result
        into a dictionary format where keys are document fragment IDs and values are their respective PageRank scores. Any exceptions,
        such as failures in running `run_pagerank_igraph_chunk`, are logged.
        """
        ppr_start_nodes = [
            GetPageRankScoresRequestStartNodes(id=node["name"], type=node["type"])
            for node in start_nodes
        ]
        req = GetPageRankScoresRequest(
            self._project_id, target_vertex_type, ppr_start_nodes
        )
        resp = self._rest_client.graph_get_page_rank_scores_post(
            get_page_rank_scores_request=req
        )
        return {item.id: item.score for item in resp}

    def write_graph(self, sub_graph: dict, operation: str, lead_to_builder: bool):
        request = WriterGraphRequest(
            project_id=self._project_id,
            sub_graph=sub_graph,
            operation=operation,
            enable_lead_to=lead_to_builder,
        )
        self._rest_client.graph_writer_graph_post(writer_graph_request=request)

    def query_vertex(self, type_name: str, biz_id: str):
        request = QueryVertexRequest(
            project_id=self._project_id, type_name=type_name, biz_id=biz_id
        )
        return self._rest_client.graph_query_vertex_post(query_vertex_request=request)

    def expend_one_hop(
        self,
        type_name: str,
        biz_id: str,
        edge_type_name_constraint: List[EdgeTypeName] = None,
    ):
        request = ExpendOneHopRequest(
            project_id=self._project_id,
            type_name=type_name,
            biz_id=biz_id,
            edge_type_name_constraint=edge_type_name_constraint,
        )
        return self._rest_client.graph_expend_one_hop_post(
            expend_one_hop_request=request
        )


if __name__ == "__main__":
    sc = GraphClient("http://127.0.0.1:8887", 4)
    out = sc.calculate_pagerank_scores(
        "Entity", [{"name": "Anxiety_and_nervousness", "type": "Entity"}]
    )
    for o in out:
        print(o)
