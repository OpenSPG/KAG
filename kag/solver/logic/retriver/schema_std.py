# coding=utf8
import sys
import os

from kag.solver.implementation.default_kg_retrieval import KGRetrieverByLlm

sys.path.append('../logic_form_executor/')
current_dir = os.path.dirname(os.path.abspath(__file__))
import logging

logger = logging.getLogger()


class SchemaRetrieval(KGRetrieverByLlm):
    def __init__(self):
        super().__init__()

    def retrieval_entity(self, entity_mention, topk=1, params={}):
        # 根据mention召回
        typed_nodes = self.graph_store.vector_search(
            label='SemanticConcept', property_key="name", query_text_or_vector=entity_mention, topk=1
        )
        if len(typed_nodes) == 0 or typed_nodes[0]["score"] < 0.8:
            return [('Entity', 1.)]
        return [(typed_nodes[0]["node"]["name"], typed_nodes[0]["score"])]
