from abc import ABC
from typing import List

from kag.interface.solver.base_model import SPOEntity
from kag.solver.logic.core_modules.common.one_hop_graph import (
    OneHopGraphData,
    KgGraph,
    EntityData,
)
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from kag.solver.retriever.base.kg_retriever import KGRetriever


class ExactKgRetriever(KGRetriever, ABC):
    def recall_one_hop_graph(
        self, n: GetSPONode, heads: List[EntityData], tails: List[EntityData], **kwargs
    ) -> List[OneHopGraphData]:
        """
        Recall one-hop graph data for a given entity.

        Parameters:
            n (GetSPONode): The entity to be standardized.
            heads (List[EntityData]): A list of candidate entities 's'.
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
