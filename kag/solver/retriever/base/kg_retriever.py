from typing import List

from kag.interface import KagBaseModule
from kag.solver.logic.core_modules.common.base_model import SPOEntity
from kag.solver.logic.core_modules.common.one_hop_graph import (
    OneHopGraphData,
    KgGraph,
    EntityData,
)
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from kag.solver.tools.graph_api.graph_api_abc import GraphApiABC
from kag.solver.tools.search_api.search_api_abc import SearchApiABC


class KGRetriever(KagBaseModule):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.schema: SchemaUtils = SchemaUtils(LogicFormConfiguration({
            "KAG_PROJECT_ID": kwargs.get("project_id"),
            "KAG_PROJECT_HOST_ADDR": kwargs.get("host_addr")
        }))
        self.graph_api = GraphApiABC.from_config({
            "type": "openspg"}
        )

        self.search_api = SearchApiABC.from_config({
            "type": "openspg"
        })

        self.text_similarity = TextSimilarity()


    def recall_one_hop_graph(self, n: GetSPONode, heads: List[EntityData], tails: List[EntityData], **kwargs) -> List[OneHopGraphData]:
        """
        Recall one-hop graph data for a given entity.

        Parameters:
            n (GetSPONode): The entity to be standardized.
            heads (List[EntityData]): A list of candidate entities.
            tails (List[EntityData]): A list of candidate entities 'o'.
            kwargs: Additional optional parameters.

        Returns:
            List[OneHopGraphData]: A list of one-hop graph data for the given entity.
        """

    def retrieval_relation(
            self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData], **kwargs
    ) -> KgGraph:
        """
        Input:
            n: GetSPONode, the relation to be standardized
            one_hop_graph_list: List[OneHopGraphData], list of candidate sets
            kwargs: additional optional parameters

        Output:
            Returns KgGraph
        """

    def retrieval_entity(
            self, mention_entity: SPOEntity, topk=1, **kwargs
    ) -> List[EntityData]:
        """
        Retrieve related entities based on the given entity mention.

        This function aims to retrieve the most relevant entities from storage or an index based on the provided entity name.

        Parameters:
            entity_mention (str): The name of the entity to retrieve.
            topk (int, optional): The number of top results to return. Defaults to 1.
            kwargs: additional optional parameters

        Returns:
            list of EntityData
        """
