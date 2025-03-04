from typing import List

from kag.interface import VectorizeModelABC
from kag.interface.solver.base_model import SPOEntity
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.core_modules.common.utils import get_recall_node_label
from kag.solver.tools.search_api.search_api_abc import SearchApiABC


def default_search_entity_by_name_algorithm(
    mention_entity: SPOEntity,
    schema: SchemaUtils,
    vectorize_model: VectorizeModelABC,
    text_similarity: TextSimilarity,
    search_api: SearchApiABC,
    topk=1,
    use_query_type=False,
    **kwargs
) -> List[EntityData]:
    """
    This function searches for entities based on a mention entity's name using various methods including vector similarity and text search.
    It returns a list of the most relevant entities up to 'topk' number of results.

    Parameters:
        mention_entity (SPOEntity): The entity mentioned in the context.
        schema (SchemaUtils): Utility object for schema operations.
        vectorize_model (VectorizeModelABC): Model used for vectorizing text.
        text_similarity (TextSimilarity): Tool for calculating text similarity.
        search_api (SearchApiABC): API for searching entities.
        topk (int): Number of top results to return.
        use_query_type (bool): Whether to use the query type for more specific searches.
        kwargs: Additional keyword arguments.

    Returns:
        List[EntityData]: A list of matched EntityData objects.
    """
    retdata = []
    if mention_entity is None:
        return retdata

    # Extract content from kwargs or use the entity name as default
    content = kwargs.get("content", mention_entity.entity_name)

    # Determine the query type based on the entity's standard type or set it to "Entity" if not specified
    query_type = mention_entity.get_entity_first_std_type()
    if query_type is None or not use_query_type:
        query_type = "Entity"
        with_prefix_type = query_type
    else:
        with_prefix_type = schema.get_label_within_prefix(query_type)

    recognition_threshold = kwargs.get("recognition_threshold", 0.8)
    recall_topk = topk

    # Adjust recall_topk if the query type is not an entity
    if "entity" not in query_type.lower():
        recall_topk = 10

    # Vectorize the entity name for vector-based search
    query_vector = vectorize_model.vectorize(mention_entity.entity_name)

    # Perform a vector-based search using the determined query type
    typed_nodes = search_api.search_vector(
        label=with_prefix_type,
        property_key="name",
        query_vector=query_vector,
        topk=recall_topk,
    )

    # Perform an additional vector-based search on the content if the query type is not "Others" or "Entity"
    if query_type not in ["Others", "Entity"]:
        content_vector = vectorize_model.vectorize(content)
        content_recall_nodes = search_api.search_vector(
            label="Entity",
            property_key="desc",
            query_vector=content_vector,
            topk=recall_topk,
        )
    else:
        content_recall_nodes = []

    # Combine the results from both searches
    sorted_nodes = typed_nodes + content_recall_nodes

    # Fallback to text-based search if no nodes are found
    if len(sorted_nodes) == 0:
        sorted_nodes = search_api.search_text(query_string=mention_entity.entity_name)

    # Re-rank the nodes based on semantic type matching if the query type is not an entity
    def rerank_sematic_type(cands_nodes: list, sematic_type: str):
        """
        Re-ranks candidate nodes based on their semantic type similarity to the provided semantic type.

        Parameters:
            cands_nodes (list): List of candidate nodes.
            sematic_type (str): The semantic type to match against.

        Returns:
            list: Re-ranked list of candidate nodes.
        """
        sematic_type_list = []
        for cands in cands_nodes:
            node = cands["node"]
            if "semanticType" not in node.keys() or node["semanticType"] == "":
                continue
            sematic_type_list.append(node["semanticType"])
        sematic_type_list = list(set(sematic_type_list))
        sematic_match_score_list = text_similarity.text_sim_result(
            sematic_type, sematic_type_list, len(sematic_type_list), low_score=-1
        )
        sematic_match_score_map = {}
        for i in sematic_match_score_list:
            sematic_match_score_map[i[0]] = i[1]
        for node in cands_nodes:
            recall_node_label = get_recall_node_label(node["node"]["__labels__"])
            if recall_node_label == sematic_type:
                node["type_match_score"] = node["score"]
            elif (
                "semanticType" not in node["node"].keys()
                or node["node"]["semanticType"] == ""
            ):
                node["type_match_score"] = 0.3
            else:
                node["type_match_score"] = (
                    node["score"]
                    * sematic_match_score_map[node["node"]["semanticType"]]
                )
        sorted_people_dicts = sorted(
            cands_nodes, key=lambda node: node["type_match_score"], reverse=True
        )
        return sorted_people_dicts[:topk]

    if "entity" not in query_type.lower():
        sorted_nodes = rerank_sematic_type(sorted_nodes, query_type)

    # Final sorting based on score
    sorted_people_dicts = sorted(
        sorted_nodes, key=lambda node: node["score"], reverse=True
    )

    # Create EntityData objects for the top results that meet the recognition threshold
    for recall in sorted_people_dicts:
        if len(sorted_people_dicts) != 0 and recall["score"] >= recognition_threshold:
            recalled_entity = EntityData()
            recalled_entity.score = recall["score"]
            recalled_entity.biz_id = recall["node"]["id"]
            recalled_entity.name = recall["node"]["name"]
            recalled_entity.type = get_recall_node_label(recall["node"]["__labels__"])
            retdata.append(recalled_entity)
        else:
            break

    return retdata[:topk]
