import logging
import time
from typing import List

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.interface import ToolABC, VectorizeModelABC
from kag.interface.solver.model.one_hop_graph import EntityData
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.text_sim_by_vector import TextSimilarity
from kag.common.utils import get_recall_node_label
from kag.common.config import LogicFormConfiguration
from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
from kag.common.tools.search_api.search_api_abc import SearchApiABC

logger = logging.getLogger()


@ToolABC.register("entity_linking")
class EntityLinking(ToolABC):
    def __init__(
        self,
        vectorize_model: VectorizeModelABC = None,
        graph_api: GraphApiABC = None,
        search_api: SearchApiABC = None,
        recognition_threshold: float = 0.8,
        top_k: int = 5,
        exclude_types: List[str] = None,
        **kwargs,
    ):
        """Initialize entity linking components with default configurations
        Args:
            vectorize_model: Text vectorization model for similarity calculation
            graph_api: Graph database access interface
            search_api: Search engine interface for vector/text search
            recognition_threshold: Minimum score threshold for valid matches
            top_k: Maximum number of results to return
            exclude_types: exclude types for entity
        """
        super().__init__()
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": kag_project_config.project_id,
                    "KAG_PROJECT_HOST_ADDR": kag_project_config.host_addr,
                }
            )
        )
        self.graph_api = graph_api or GraphApiABC.from_config(
            {"type": "openspg_graph_api"}
        )

        self.search_api = search_api or SearchApiABC.from_config(
            {"type": "openspg_search_api"}
        )

        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            kag_config.all_config["vectorize_model"]
        )
        self.text_similarity = TextSimilarity(vectorize_model)
        self.recognition_threshold = recognition_threshold
        self.top_k = top_k
        self.exclude_types = exclude_types

    # Re-rank the nodes based on semantic type matching if the query type is not an entity
    def rerank_sematic_type(self, candis_nodes: list, sematic_type: str):
        """Re-rank candidate nodes based on semantic type similarity
        Args:
            candis_nodes: List of candidate nodes with scores
            sematic_type: Target semantic type for matching
        Returns:
            Re-ranked list of nodes prioritized by type match scores
        """
        sematic_type_list = []
        for candis in candis_nodes:
            node = candis["node"]
            if "semanticType" not in node.keys() or node["semanticType"] == "":
                continue
            sematic_type_list.append(node["semanticType"])
        sematic_type_list = list(set(sematic_type_list))
        sematic_match_score_list = self.text_similarity.text_sim_result(
            sematic_type, sematic_type_list, len(sematic_type_list), low_score=-1
        )
        sematic_match_score_map = {}
        for i in sematic_match_score_list:
            sematic_match_score_map[i[0]] = i[1]
        for node in candis_nodes:
            recall_node_label = get_recall_node_label(node["node"]["__labels__"])
            without_prefix_label = self.schema_helper.get_label_without_prefix(
                recall_node_label
            )
            if without_prefix_label.lower() == sematic_type.lower():
                node["type_match_score"] = node["score"]
            elif (
                "semanticType" not in node["node"].keys()
                or node["node"]["semanticType"] == ""
            ):
                node["type_match_score"] = 0.3 * node["score"]
            else:
                type_score = sematic_match_score_map[node["node"]["semanticType"]]
                if type_score < 0.6:
                    type_score = 0.3
                node["type_match_score"] = node["score"] * type_score
        sorted_people_dicts = sorted(
            candis_nodes, key=lambda n: n["type_match_score"], reverse=True
        )
        return sorted_people_dicts[: self.top_k]

    def filter_target_types(self, type_nodes):
        if self.exclude_types is None:
            return type_nodes
        result = []
        for node in type_nodes:
            recall_node_label = get_recall_node_label(node["node"]["__labels__"])
            label_name = self.schema_helper.get_label_without_prefix(recall_node_label)
            if label_name in self.exclude_types:
                continue
            result.append(node)
        return result

    def recall_entity(
        self, query: str, name: str, type_name: str = None, topk_k: int = None
    ):
        # Determine the query type based on the entity's standard type or set it to "Entity" if not specified
        query_type = type_name
        if query_type is None:
            query_type = "Entity"
            with_prefix_type = query_type
        else:
            with_prefix_type = self.schema_helper.get_label_within_prefix(query_type)
            if with_prefix_type == query_type:
                with_prefix_type = "Entity"

        try:

            recall_topk = topk_k or self.top_k

            # Adjust recall_topk if the query type is not an entity
            if "entity" not in query_type.lower():
                recall_topk = 10

            vectorize_start_time = time.time()
            # Vectorize the entity name for vector-based search
            query_vector = self.vectorize_model.vectorize(name)
            logger.info(
                f"`{name}` Vectorization completed in {time.time() - vectorize_start_time:.2f} seconds."
            )

            vector_search_start_time = time.time()
            # Perform a vector-based search using the determined query type
            typed_nodes = self.search_api.search_vector(
                label=with_prefix_type,
                property_key="name",
                query_vector=query_vector,
                topk=recall_topk,
            )
            logger.info(
                f"`{name}` Vector-based search completed in {time.time() - vector_search_start_time:.2f} seconds. Found {len(typed_nodes)} nodes."
            )
            if len(typed_nodes) == 0:
                vector_search_entity_start_time = time.time()
                typed_nodes = self.search_api.search_vector(
                    label="Entity",
                    property_key="name",
                    query_vector=query_vector,
                    topk=recall_topk,
                )
                logger.info(
                    f"`{name}` Vector-based search with label: Entity completed in {time.time() - vector_search_entity_start_time:.2f} seconds. Found {len(typed_nodes)} nodes."
                )

            # Perform an additional vector-based search on the content if the query type is not "Others" or "Entity"

            if query_type not in ["Others", "Entity"]:
                content_search_start_time = time.time()
                content_vector = self.vectorize_model.vectorize(query)
                content_recall_nodes = self.search_api.search_vector(
                    label="Entity",
                    property_key="desc",
                    query_vector=content_vector,
                    topk=recall_topk,
                )
                logger.info(
                    f"`{name}` Content-based vector search completed in {time.time() - content_search_start_time:.2f} seconds. Found {len(content_recall_nodes)} nodes."
                )
            else:
                content_recall_nodes = []
            # Combine the results from both searches
            sorted_nodes = typed_nodes + content_recall_nodes
            sorted_nodes = self.filter_target_types(sorted_nodes)

            # Fallback to text-based search if no nodes are found
            if len(sorted_nodes) == 0:
                sorted_nodes = self.search_api.search_text(query_string=name)
            return sorted_nodes
        except Exception as e:
            logger.error(
                f"Error in entity_linking {query} name={name} type={with_prefix_type}: {e}",
                exc_info=True,
            )
            return []

    def invoke(self, query, name, type_name, topk_k=None, **kwargs) -> List[EntityData]:
        """Perform entity linking by combining vector and text search strategies
        Args:
            query: Original text context containing the entity
            name: Entity name to link
            type_name: Entity type (e.g., Person, Location)
            topk_k: Maximum number of results to return
            recognition_threshold: Minimum score threshold (default 0.8)
        Returns:
            List of matched entities with scores and metadata
        """
        # Implementation logic with detailed steps:
        # 1. Determine query type and adjust parameters
        # 2. Vector search based on entity name
        # 3. Content-based vector search for non-basic types
        # 4. Text search fallback
        # 5. Semantic type re-ranking
        # 6. Final filtering and sorting
        if not topk_k:
            topk_k = self.top_k
        recognition_threshold = kwargs.get(
            "recognition_threshold", self.recognition_threshold
        )
        retdata = []
        if name is None:
            return retdata

        try:
            if isinstance(type_name, str):
                type_name_set = [type_name]
            else:
                type_name_set = type_name
            total_recall_entities = []
            for type_name in type_name_set:
                recall_nodes = self.recall_entity(query, name, type_name, topk_k * 5)
                total_recall_entities += recall_nodes

            # Final sorting based on score
            sorted_people_dicts = sorted(
                total_recall_entities, key=lambda node: node["score"], reverse=True
            )

            # Create EntityData objects for the top results that meet the recognition threshold
            for recall in sorted_people_dicts:
                if (
                    len(sorted_people_dicts) != 0
                    and recall["score"] >= recognition_threshold
                ):
                    recalled_entity = EntityData()
                    recalled_entity.score = recall["score"]
                    recalled_entity.biz_id = recall["node"]["id"]
                    recalled_entity.name = recall["node"]["name"]
                    recalled_entity.set_properties(recall["node"])
                    recalled_entity.type = get_recall_node_label(
                        recall["node"]["__labels__"]
                    )
                    retdata.append(recalled_entity)
                else:
                    break

            return retdata[:topk_k]
        except Exception as e:
            logger.error(
                f"Error in entity_linking {query} name={name} type={type_name}: {e}",
                exc_info=True,
            )
            return []

    def schema(self):
        return {
            "name": "entity_linking",
            "description": "Link entities in input text to corresponding entities in knowledge graph",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Original text that needs entity linking",
                    },
                    "name": {
                        "type": "string",
                        "description": "Name of the entity to be linked",
                    },
                    "type_name": {
                        "type": "string",
                        "description": "Entity type, such as person, location, organization, etc.",
                    },
                },
                "required": ["query", "name", "type_name"],
            },
        }
