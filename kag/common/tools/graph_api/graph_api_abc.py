from abc import abstractmethod
from typing import Dict, List

from kag.common.registry import Registrable
from kag.interface.solver.base_model import SPOEntity, SPOBase
from kag.interface.solver.model.one_hop_graph import (
    EntityData,
    OneHopGraphData,
)
from kag.common.tools.graph_api.model.table_model import TableData


def replace_qota(s: str):
    return s.replace('"', '\\"')


def generate_label(s: SPOBase, heads: List[EntityData], schema):
    if heads:
        return list(set([f"`{h.type}`" for h in heads]))

    if not isinstance(s, SPOEntity):
        return ["Entity"]

    std_types = s.get_entity_type_set()
    std_types_with_prefix = []
    for std_type in std_types:
        std_type_with_prefix = schema.get_label_within_prefix(std_type)
        if std_types_with_prefix != std_type:
            std_types_with_prefix.append(f"`{std_type_with_prefix}`")
    if len(std_types_with_prefix):
        return list(set(std_types_with_prefix))
    return ["Entity"]


def generate_gql_id_params(ids: List[str]):
    s_biz_id_set = [f'"{replace_qota(biz_id)}"' for biz_id in ids]
    return f'[{",".join(s_biz_id_set)}]'


class GraphApiABC(Registrable):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def get_entity_prop_by_id(self, biz_id, label) -> Dict:
        pass

    @abstractmethod
    def get_entity(self, entity: SPOEntity) -> List[EntityData]:
        pass

    @abstractmethod
    def get_entity_one_hop(self, entity: EntityData) -> OneHopGraphData:
        pass

    @abstractmethod
    def convert_spo_to_one_graph(self, table: TableData) -> Dict[str, OneHopGraphData]:
        pass

    @abstractmethod
    def execute_dsl(self, dsl: str, **kwargs) -> TableData:
        pass

    @abstractmethod
    def calculate_pagerank_scores(
        self, target_vertex_type, start_nodes: List[Dict], top_k=10
    ) -> Dict:
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
