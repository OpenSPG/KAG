from abc import abstractmethod
from typing import Dict, List

from kag.common.registry import Registrable
from kag.interface.solver.base_model import SPOEntity, SPOBase
from kag.interface.solver.model.one_hop_graph import (
    EntityData,
    OneHopGraphData,
)
from kag.tools.graph_api.model.table_model import TableData


def replace_qota(s: str):
    return s.replace('"', '\\"')


def generate_label(s: SPOBase, heads: List[EntityData], schema):
    if heads:
        return list(set([f"{h.type}" for h in heads]))

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


class GraphStoreApiABC(Registrable):
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

    @abstractmethod
    def search_text(
        self, query_string, label_constraints=None, topk=10, params=None
    ) -> List:
        pass

    @abstractmethod
    def search_vector(
        self, label, property_key, query_vector, topk=10, ef_search=None, params=None
    ) -> List:
        pass

    @abstractmethod
    def search_custom(self, custom_query, params=None) -> List:
        pass

    @abstractmethod
    def close(self):
        """
        Close the graph store resources.
        """

    @abstractmethod
    def initialize_schema(self, schema):
        """
        Initialize the graph schema.

        Parameters:
        - schema: Definition of the graph schema.
        """

    @abstractmethod
    def upsert_node(self, label, properties, id_key="id", extra_labels=("Entity",)):
        """
        Insert or update a single node.

        Parameters:
        - label: Label of the node.
        - properties: Properties of the node.
        - id_key: Property key used as the unique identifier.
        - extra_labels: Additional labels for the node.
        """

    @abstractmethod
    def upsert_nodes(
        self, label, properties_list, id_key="id", extra_labels=("Entity",)
    ):
        """
        Insert or update multiple nodes.

        Parameters:
        - label: Label of the nodes.
        - properties_list: List of properties for the nodes.
        - id_key: Property key used as the unique identifier.
        - extra_labels: Additional labels for the nodes.
        """

    @abstractmethod
    def batch_preprocess_node_properties(self, node_batch, extra_labels=("Entity",)):
        """
        Batch preprocess node properties.

        Parameters:
        - node_batch: A batch of nodes.
        - extra_labels: Additional labels for the nodes.
        """

    @abstractmethod
    def get_node(self, label, id_value, id_key="id"):
        """
        Get a node by label and identifier.

        Parameters:
        - label: Label of the node.
        - id_value: Unique identifier value of the node.
        - id_key: Property key used as the unique identifier.

        Returns:
        - The matching node.
        """

    @abstractmethod
    def delete_node(self, label, id_value, id_key="id"):
        """
        Delete a specified node.

        Parameters:
        - label: Label of the node.
        - id_value: Unique identifier value of the node.
        - id_key: Property key used as the unique identifier.
        """

    @abstractmethod
    def delete_nodes(self, label, id_values, id_key="id"):
        """
        Delete multiple nodes.

        Parameters:
        - label: Label of the nodes.
        - id_values: List of unique identifier values for the nodes.
        - id_key: Property key used as the unique identifier.
        """

    @abstractmethod
    def upsert_relationship(
        self,
        start_node_label,
        start_node_id_value,
        end_node_label,
        end_node_id_value,
        rel_type,
        properties,
        upsert_nodes=True,
        start_node_id_key="id",
        end_node_id_key="id",
    ):
        """
        Insert or update a relationship.

        Parameters:
        - start_node_label: Label of the start node.
        - start_node_id_value: Unique identifier value of the start node.
        - end_node_label: Label of the end node.
        - end_node_id_value: Unique identifier value of the end node.
        - rel_type: Type of the relationship.
        - properties: Properties of the relationship.
        - upsert_nodes: Whether to insert or update nodes.
        - start_node_id_key: Property key used as the unique identifier for the start node.
        - end_node_id_key: Property key used as the unique identifier for the end node.
        """

    @abstractmethod
    def upsert_relationships(
        self,
        start_node_label,
        end_node_label,
        rel_type,
        relationships,
        upsert_nodes=True,
        start_node_id_key="id",
        end_node_id_key="id",
    ):
        """
        Insert or update multiple relationships.

        Parameters:
        - start_node_label: Label of the start node.
        - end_node_label: Label of the end node.
        - rel_type: Type of the relationship.
        - relationships: List of relationships.
        - upsert_nodes: Whether to insert or update nodes.
        - start_node_id_key: Property key used as the unique identifier for the start node.
        - end_node_id_key: Property key used as the unique identifier for the end node.
        """

    @abstractmethod
    def delete_relationship(
        self,
        start_node_label,
        start_node_id_value,
        end_node_label,
        end_node_id_value,
        rel_type,
        start_node_id_key="id",
        end_node_id_key="id",
    ):
        """
        Delete a specified relationship.

        Parameters:
        - start_node_label: Label of the start node.
        - start_node_id_value: Unique identifier value of the start node.
        - end_node_label: Label of the end node.
        - end_node_id_value: Unique identifier value of the end node.
        - rel_type: Type of the relationship.
        - start_node_id_key: Property key used as the unique identifier for the start node.
        - end_node_id_key: Property key used as the unique identifier for the end node.
        """

    @abstractmethod
    def delete_relationships(
        self,
        start_node_label,
        start_node_id_values,
        end_node_label,
        end_node_id_values,
        rel_type,
        start_node_id_key="id",
        end_node_id_key="id",
    ):
        """
        Delete multiple relationships.

        Parameters:
        - start_node_label: Label of the start node.
        - start_node_id_values: List of unique identifier values for the start nodes.
        - end_node_label: Label of the end node.
        - end_node_id_values: List of unique identifier values for the end nodes.
        - rel_type: Type of the relationship.
        - start_node_id_key: Property key used as the unique identifier for the start node.
        - end_node_id_key: Property key used as the unique identifier for the end node.
        """

    @abstractmethod
    def create_index(self, label, property_key, index_name=None):
        """
        Create a node index.

        Parameters:
        - label: Label of the node.
        - property_key: Property key used for indexing.
        - index_name: Name of the index (optional).
        """

    @abstractmethod
    def create_text_index(self, labels, property_keys, index_name=None):
        """
        Create a text index.

        Parameters:
        - labels: List of node labels.
        - property_keys: List of property keys used for indexing.
        - index_name: Name of the index (optional).
        """

    @abstractmethod
    def create_vector_index(
        self,
        label,
        property_key,
        index_name=None,
        vector_dimensions=768,
        metric_type="cosine",
        hnsw_m=None,
        hnsw_ef_construction=None,
    ):
        """
        Create a vector index.

        Parameters:
        - label: Label of the node.
        - property_key: Property key used for indexing.
        - index_name: Name of the index (optional).
        - vector_dimensions: Dimensionality of the vectors, default is 768.
        - metric_type: Type of distance measure, default is "cosine".
        - hnsw_m: m parameter of the HNSW algorithm, default to None (for m=16)
        - hnsw_ef_construction: ef_construction parameter of the HNSW algorithm, default to None (for ef_construction=100)
        """

    @abstractmethod
    def delete_index(self, index_name):
        """
        Delete a specified index.

        Parameters:
        - index_name: Name of the index.
        """

    @abstractmethod
    def text_search(
        self, query_string, label_constraints=None, topk=10, index_name=None
    ):
        """
        Perform a text search.

        Parameters:
        - query_string: Query string.
        - label_constraints: Label constraints (optional).
        - topk: Number of top results to return, default is 10.
        - index_name: Name of the index (optional).

        Returns:
        - List of search results.
        """

    @abstractmethod
    def vector_search(
        self,
        label,
        property_key,
        query_text_or_vector,
        topk=10,
        index_name=None,
        ef_search=None,
    ):
        """
        Perform a vector search.

        Parameters:
        - label: Label of the node.
        - property_key: Property key used for indexing.
        - query_text_or_vector: Query text or vector.
        - topk: Number of top results to return, default is 10.
        - index_name: Name of the index (optional).
        - ef_search: ef_search parameter of the HNSW algorithm, specify number of potential candicates

        Returns:
        - List of search results.
        """

    @abstractmethod
    def execute_pagerank(self, iterations=20, damping_factor=0.85):
        """
        Execute the PageRank algorithm.

        Parameters:
        - iterations: Number of iterations, default is 20.
        - damping_factor: Damping factor, default is 0.85.
        """

    @abstractmethod
    def get_pagerank_scores(self, start_nodes, target_type):
        """
        Get PageRank scores.

        Parameters:
        - start_nodes: Start nodes.
        - target_type: Target node type.

        Returns:
        - PageRank scores.
        """

    @abstractmethod
    def run_script(self, script):
        """
        Execute a script.

        Parameters:
        - script: Script to be executed.
        """

    @abstractmethod
    def get_all_entity_labels(self):
        """
        Get all entity labels.

        Returns:
        - List of entity labels.
        """
