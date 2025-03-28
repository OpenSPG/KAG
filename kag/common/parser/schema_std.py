# coding=utf8
from kag.common.registry import Registrable

import logging

from typing import List

from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF
from kag.interface import VectorizeModelABC
from kag.interface.solver.base_model import SPOEntity
from kag.interface.solver.model.one_hop_graph import (
    EntityData,
)
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.text_sim_by_vector import TextSimilarity
from kag.common.config import LogicFormConfiguration
from kag.tools.search_api.search_api_abc import SearchApiABC

logger = logging.getLogger()


class StdSchema(Registrable):
    def __init__(self, vectorize_model: VectorizeModelABC = None, search_api: SearchApiABC = None, **kwargs):
        super().__init__(**kwargs)
        self.schema: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
                }
            )
        )
        self.search_api = search_api or SearchApiABC.from_config(
            {"type": "openspg_search_api"}
        )

        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            KAG_CONFIG.all_config["vectorize_model"]
        )
        self.text_similarity = TextSimilarity(vectorize_model)

    def retrieval_entity(self, mention_entity: SPOEntity, **kwargs) -> List[EntityData]:
        """
        Retrieve related entities based on the given entity mention.

        This function aims to retrieve the most relevant entities from storage or an index based on the provided entity name.

        Parameters:
            entity_mention (str): The name of the entity to retrieve.
            kwargs: additional optional parameters

        Returns:
            list of EntityData
        """

@StdSchema.register("default_std_schema")
class DefaultStdSchema(StdSchema):
    def __init__(self, vectorize_model: VectorizeModelABC = None, search_api: SearchApiABC = None, **kwargs):
        super().__init__(vectorize_model=vectorize_model, search_api=search_api, **kwargs)

    def retrieval_entity(self, mention_entity: SPOEntity, **kwargs) -> List[EntityData]:
        # 根据mention召回
        label = self.schema.get_label_within_prefix("SemanticConcept")
        typed_nodes = self.search_api.search_vector(
            label=label,
            property_key="name",
            query_vector=self.vectorize_model.vectorize(mention_entity.entity_name),
            topk=1,
        )
        if typed_nodes is None:
            return []
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
