# coding=utf8
from kag.common.registry import Registrable

import logging

from typing import List

from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF
from kag.common.utils import resolve_instance
from kag.interface import VectorizeModelABC
from kag.interface.solver.base_model import SPOEntity
from kag.interface.solver.model.one_hop_graph import (
    EntityData,
)
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.text_sim_by_vector import TextSimilarity
from kag.common.config import LogicFormConfiguration
from kag.tools.search_api.search_api_abc import SearchApiABC
from kag.jiuyuansolver.pg_impl import PostgresDB

logger = logging.getLogger()


class StdSchema(Registrable):
    def __init__(
        self,
        vectorize_model: VectorizeModelABC = None,
        search_api: SearchApiABC = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.schema: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
                }
            )
        )
        self.search_api = resolve_instance(
            search_api,
            default_config={"type": "openspg_search_api"},
            from_config_func=SearchApiABC.from_config,
        )

        self.vectorize_model = resolve_instance(
            vectorize_model,
            default_config=KAG_CONFIG.all_config["vectorize_model"],
            from_config_func=VectorizeModelABC.from_config,
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
    def __init__(
        self,
        vectorize_model: VectorizeModelABC = None,
        search_api: SearchApiABC = None,
        **kwargs
    ):
        super().__init__(
            vectorize_model=vectorize_model, search_api=search_api, **kwargs
        )
    

    def retrieval_entity(self, mention_entity: SPOEntity, **kwargs) -> List[EntityData]:
        # 根据mention召回
        label = self.schema.get_label_within_prefix("SemanticConcept")
        # typed_nodes = self.search_api.search_vector(
        #     label=label,
        #     property_key="name",
        #     query_vector=self.vectorize_model.vectorize(mention_entity.entity_name),
        #     topk=1,
        # )

        db_config = {
            "host": "localhost",
            "port": 5432,
            "user": "wr",
            "password": "your_password",
            "database": "test"
        }
        # 创建数据库连接
        db = PostgresDB(db_config)

        try:
            # 连接数据库
            db.sync_connect()
            
            # 搜索最相似的节点
            typed_nodes = db.sync_find_most_similar_vector(
                node_type = label,
                property_key="name",
                vector=self.vectorize_model.vectorize(mention_entity.entity_name),
                table="graph_nodes",
                threshold=-1,
                topk=1
            )
        except Exception as e:
            logger.error(f"搜索过程中出错: {str(e)}")
        finally:
            db.sync_close()


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
