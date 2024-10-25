from abc import ABC, abstractmethod
from typing import List

from kag.solver.common.base import KagBaseModule
from kag.solver.logic.core_modules.common.base_model import SPOEntity
from kag.solver.logic.core_modules.common.one_hop_graph import OneHopGraphData, KgGraph, EntityData
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode


class KGRetrieverABC(KagBaseModule, ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    """
    A base class for knowledge graph retrieval strategies.

    This class provides a template for implementing different retrieval strategies for relations and entities within a knowledge graph.

    Methods:
        retrieval_relation(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData], **kwargs) -> KgGraph:
            Retrieves and standardizes relations based on the given node and one hop graph list.

        retrieval_entity(entity_mention, topk=1, params={}):
            Retrieves related entities based on the given entity mention.
    """
    @abstractmethod
    def retrieval_relation(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData], **kwargs) -> KgGraph:
        '''
        Input:
            n: GetSPONode, the relation to be standardized
            one_hop_graph_list: List[OneHopGraphData], list of candidate sets
            kwargs: additional optional parameters

        Output:
            Returns KgGraph
        '''

    @abstractmethod
    def retrieval_entity(self, mention_entity: SPOEntity, topk=1, **kwargs) -> List[EntityData]:
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
