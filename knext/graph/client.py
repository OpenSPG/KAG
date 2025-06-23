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
from jiuyuan_db.client.client import JiuyuanClient
from jiuyuan_db.model.filter import SingleFilter, MemoryGraphFilter, VERTEX_TYPE, EDGE_TYPE
from jiuyuan_db.job_config import AnalyticJobConfig, AnalyticJobConfigConstant, AnalyticJobEnum, AnalyticNode
import json
import os

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
        # req = GetPageRankScoresRequest(
        #     self._project_id, target_vertex_type, ppr_start_nodes
        # )

        # resp = self._rest_client.graph_get_page_rank_scores_post(
        #     get_page_rank_scores_request=req
        # )
        jyresp = []

        jiuyuan_client=JiuyuanClient(host='localhost',
                            port=12321,
                            user='wr',
                            password='',
                            database_name='test')

        try:
            session = jiuyuan_client.get_session()
            graph = session.create_graph("test622", True)
            graph_id = graph.graph_id

            start_ids = []
            print("ppr_start_nodes:")
            print(ppr_start_nodes)
            for item in ppr_start_nodes:
                node_label = item.type.split('.')[-1]
                node_id = item.id
                cypherQuery = "MATCH (n:%s) WHERE n.id='%s' RETURN id(n) AS id" % (node_label, node_id)
                res = session.execute_query(graph_id=graph_id, query=cypherQuery)
                print("res")
                print(res)
                for nod in res.get_result_list():
                    start_ids.append(nod[0])

            print("start_ids")
            print(start_ids)

            roots = ", ".join(start_ids) 
            

            # create filters
            vertex_filter = SingleFilter(entity_type=VERTEX_TYPE, label_name='_ag_label_vertex')
            edge_filter = SingleFilter(entity_type=EDGE_TYPE, label_name='_ag_label_edge')
            filters = MemoryGraphFilter(filters=[vertex_filter, edge_filter])
            print(filters.to_dict())
            # project graph to memory graph
            memory_graph = session.project_graph(graph_id=graph_id, filters=filters)

            memory_graph_id = memory_graph.id
            print(memory_graph_id)
            # run analytic job
            result = session.run_graph_algorithm(memory_graph_id=[memory_graph_id], algorithm_name="ppr",
                                    args_dict={"output_dir":"/root/softwares/kag_project/KAG-master/kag/jiuyuansolver/output", "roots":roots}, return_result=True)
                                    # ./bin/ppr --vertex_csv_files /tmp/jiuyuan/memorygraph/vertexs.csv --edge_csv_files /tmp/jiuyuan/memorygraph/edges.csv  --output_dir ./output  --roots "844424930131970,844424930131972"
                                    # /root/softwares/kag_project/jiuyuan_graphdb-master/graph_algorithm_standalone/procedures/bin/ppr --vertex_csv_files /tmp/jiuyuan/memorygraph/22461_0_1750554780__ag_label_vertex.csv --edge_csv_files /tmp/jiuyuan/memorygraph/22461_0_1750554780__ag_label_edge.csv --output_dir /root/softwares/kag_project/KAG-master/kag/jiuyuansolver/output2 --roots 0,1
                                    #  ./bin/ppr --vertex_csv_files /tmp/jiuyuan/memorygraph/vertexs.csv --edge_csv_files /tmp/jiuyuan/memorygraph/edges.csv  --output_dir /root/softwares/kag_project/KAG-master/kag/jiuyuansolver/output2  --roots "844424930131970,844424930131972"


            file_paths =  "/root/softwares/kag_project/KAG-master/kag/jiuyuansolver/output/ppr.json"

            def parse_ppr_data(file_path):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    # 提取基本信息
                    result = data.get('result', {})
                    # 提取并排序分数
                    scores = result.get('scores', {})
                    # 返回解析结果
                    return scores
                except FileNotFoundError:
                    print(f"错误: 文件 '{file_path}' 不存在")
                except json.JSONDecodeError:
                    print(f"错误: 文件 '{file_path}' 不是有效的JSON格式")
                except Exception as e:
                    print(f"发生未知错误: {e}")
            
            scores = parse_ppr_data(file_paths)
            target_node_label = target_vertex_type.split('.')[-1]
            cypherQuery = "MATCH (n:%s) RETURN id(n) AS real_id, n.id as id" % (target_node_label)
            res = session.execute_query(graph_id=graph_id, query=cypherQuery)

            id_mapping = {item[0]: item[1].strip('"') for item in res.get_result_list()}

            jyresp = [
                {
                    'id': id_mapping.get(node_id, node_id),
                    'score': round(score, 8),
                    'type':target_vertex_type
                }
                for node_id, score in scores.items()
                if node_id in id_mapping
            ]

            jyresp.sort(key=lambda x: x['score'], reverse=True)

            print("jyresp")
            print(jyresp)

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            jiuyuan_client.release_session(session)
        

        # return {item.id: item.score for item in resp}
        return {item['id']: item['score'] for item in jyresp}

    def write_graph(self, sub_graph: dict, operation: str, lead_to_builder: bool):
        request = WriterGraphRequest(
            project_id=self._project_id,
            sub_graph=sub_graph,
            operation=operation,
            enable_lead_to=lead_to_builder,
            token="openspg@8380255d4e49_"
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
    sc = GraphClient("http://127.0.0.1:8887", 1)
    
    # out = sc.calculate_pagerank_scores(
    #     "Entity", [{"name": "Anxiety_and_nervousness", "type": "Entity"}]
    # )
    target_vertex_type = "TwoWikiTest.Chunk"
    start_nodes=[{'id': '中国', 'name': '中国', 'type': 'TwoWikiTest.Others'}, {'id': '稀土', 'name': '稀土', 'type': 'TwoWikiTest.NaturalScience'}]
    out = sc.calculate_pagerank_scores(
        target_vertex_type, start_nodes
    )

    for o in out:
        print(o)
