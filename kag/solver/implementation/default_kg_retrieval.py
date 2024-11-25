# coding=utf8
import os
from typing import List

from kag.common.graphstore.neo4j_graph_store import Neo4jClient
from kag.interface.retriever.kg_retriever_abc import KGRetrieverABC
from kag.common.vectorizer import Vectorizer
from kag.solver.logic.common.one_hop_graph import KgGraph, OneHopGraphData
from kag.solver.logic.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.parser.logic_node_parser import GetSPONode
from kag.solver.logic.retriver.retrieval_spo import FuzzyMatchRetrievalSpo
# from knext.common.semantic_infer import SemanticEnhance

current_dir = os.path.dirname(os.path.abspath(__file__))
import logging

logger = logging.getLogger()


class KGRetrieverByLlm(KGRetrieverABC):  # , SemanticEnhance
    """
    A subclass of KGRetrieval that implements relation and entity retrieval using large language models.

    This class provides the default implementation for retrieving relations and entities within the system,
    leveraging large language models for its operations.
    """

    def __init__(self):
        self.text_similarity = TextSimilarity()
        graph_store_config = eval(os.getenv("KAG_GRAPH_STORE"))
        graph_store = Neo4jClient(
            **graph_store_config
        )
        graph_store.vectorizer = Vectorizer.from_config(eval(os.getenv("KAG_VECTORIZER")))
        self.graph_store = graph_store
        self.fuzzy_match = FuzzyMatchRetrievalSpo()
        self.with_fix_onto = eval(os.getenv("KAG_RETRIEVER_WITH_SEMANTIC_FIX_ONTO", "True"))
        # TODO
        # self.with_semantic_hyper = eval(os.getenv("KAG_RETRIEVER_WITH_SEMANTIC_HYPER_EXPAND", "True"))
        # if self.with_semantic_hyper:
        #     SemanticEnhance.__init__(self)

    def retrieval_relation(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData], **kwargs) -> KgGraph:
        # raise RuntimeError
        return self.fuzzy_match.match_spo(n, one_hop_graph_list)

    def retrieval_entity(self, entity_mention, topk=5, **params):
        content = params.get('content', entity_mention)
        query_type = params.get('label', 'Entity')
        recognition_threshold = params.get('recognition_threshold', 0.8)

        # vector recall
        name_recall = self.graph_store.vector_search(
            label="Entity", property_key="name", query_text_or_vector=entity_mention, topk=topk * 2
        )
        name_recall = [n for n in name_recall if 'Chunk' not in n['label']][:topk]  # filter out Chunk
        content_recall_nodes = self.graph_store.vector_search(
            label="Entity", property_key="desc", query_text_or_vector=content, topk=topk
        ) if query_type not in ["Others", "Entity"] else []
        recall_nodes = name_recall + content_recall_nodes

        # rerank
        def rerank_with_onto_type(target_onto: str, cand_nodes: list):
            """
            adjust score with node onto similarity
            """
            cand_types = {cand['node'].get('semanticType', '') for cand in cand_nodes}
            cand_types = [t for t in cand_types if t != '']
            type_score_list = self.text_similarity.text_sim_result(
                target_onto, cand_types, len(cand_types), low_score=-1
            )
            type_score_map = {name: score for name, score in type_score_list}
            for node in cand_nodes:
                n_type = node['node'].get('semanticType', '')
                node['type_match_score'] = type_score_map.get(n_type, 0.5) * node['score']
                # node['score'] *= type_score_map.get(n_type, 0.5)
            sorted_cand_nodes = sorted(cand_nodes, key=lambda x: x['type_match_score'], reverse=True)
            cand_nodes = sorted_cand_nodes[:topk]
            return cand_nodes

        if query_type != 'Entity' and self.with_fix_onto:
            recall_nodes = rerank_with_onto_type(target_onto=query_type, cand_nodes=recall_nodes)

        sorted_recall = sorted(recall_nodes, key=lambda node: node['score'], reverse=True)

        retrieved_res = {"word": entity_mention, "recall": []}
        for ix, recall in enumerate(sorted_recall[:topk]):
            if ix == 0 or recall["score"] >= recognition_threshold:
                retrieved_res['recall'].append({
                    'subject_id': recall["node"]["id"],
                    'name': recall["node"]["name"],
                    'type': 'Entity',
                    'match_score': recall["score"]
                })
            else:
                break
        return {
            'content': content,
            'entities': [
                retrieved_res
            ]
        }
