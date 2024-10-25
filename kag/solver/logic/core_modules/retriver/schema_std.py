# coding=utf8
import os
import sys
from typing import List

from kag.solver.implementation.default_kg_retrieval import KGRetrieverByLlm
from kag.solver.logic.core_modules.common.base_model import SPOEntity
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData

sys.path.append('../logic_form_executor/')
current_dir = os.path.dirname(os.path.abspath(__file__))
import logging

logger = logging.getLogger()


class SchemaRetrieval(KGRetrieverByLlm):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def retrieval_entity(self, mention_entity: SPOEntity, topk=1, **kwargs) -> List[EntityData]:
        # 根据mention召回
        label = self.schema.get_label_within_prefix('SemanticConcept')
        typed_nodes = self.sc.search_vector(
            label=label, property_key="name", query_vector=self.vectorizer.vectorize(mention_entity.entity_name), topk=1
        )
        recalled_entity = EntityData()
        recalled_entity.type = "SemanticConcept"
        if len(typed_nodes) == 0 or typed_nodes[0]["score"] < 0.9:
            recalled_entity = EntityData()
            recalled_entity.biz_id = "Entity"
            recalled_entity.name = "Entity"
            return [recalled_entity]
        recalled_entity.biz_id = typed_nodes[0]["node"]["name"]
        recalled_entity.name = typed_nodes[0]["node"]["name"]
        recalled_entity.score = typed_nodes[0]["score"]
        return [recalled_entity]
