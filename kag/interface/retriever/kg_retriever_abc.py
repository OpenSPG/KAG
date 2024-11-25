from abc import ABC, abstractmethod
from typing import List

from kag.solver.logic.common.one_hop_graph import OneHopGraphData, KgGraph
from kag.solver.logic.parser.logic_node_parser import GetSPONode


class KGRetrieverABC(ABC):
    """
    A base class for knowledge graph retrieval strategies.

    This class provides a template for implementing different retrieval strategies for relations and entities within a knowledge graph.

    Methods:
        retrieval_relation(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData], **kwargs) -> KgGraph:
            Retrieves and standardizes relations based on the given node and one hop graph list.

        retrieval_entity(entity_mention, topk=1, params={}):
            Retrieves related entities based on the given entity mention.
    """
    ## @雪酒，这里的返回值需要明确定义
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

    ## @雪酒，这里的返回值需要明确定义；如果返回值可能是两种结果，建议通过两个方法来实现
    @abstractmethod
    def retrieval_entity(self, entity_mention, topk=1, params={}):
        """
        Retrieve related entities based on the given entity mention.

        This function aims to retrieve the most relevant entities from storage or an index based on the provided entity name.

        Parameters:
            entity_mention (str): The name of the entity to retrieve.
            topk (int, optional): The number of top results to return. Defaults to 1.
            params (dict, optional): Additional parameters for retrieval. Defaults to {}.

        Returns:
            Depending on the implementation, this could return a list of entities or some form of structured data containing the retrieved information.
        """
