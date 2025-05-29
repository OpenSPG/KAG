import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

from kag.common.parser.logic_node_parser import GetSPONode
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.model.one_hop_graph import RetrievedData, ChunkData
from knext.schema.client import CHUNK_TYPE

logger = logging.getLogger()


def get_history_qa(history: List[LogicNode]):
    history_qa = []
    for idx, lf in enumerate(history):
        if (
            lf.get_fl_node_result().summary != ""
            and "i don't know" not in lf.get_fl_node_result().summary.lower()
        ):
            history_qa.append(
                f"step{idx}:{lf.get_fl_node_result().sub_question}\nanswer:{lf.get_fl_node_result().summary}"
            )
    return history_qa


def generate_step_query(
    logical_node: GetSPONode, processed_logical_nodes: List[LogicNode], start_index=0
):
    sub_queries = []
    index = start_index
    for processed_logical_node in processed_logical_nodes:
        index += 1
        sub_queries.append(
            f"Step{index}: {processed_logical_node.sub_query}\n{processed_logical_node.get_fl_node_result().summary}"
        )
    sub_queries.append(logical_node.sub_query)
    sub_query = "\n".join(sub_queries)
    return sub_query


def get_chunks(input_data: List[RetrievedData]) -> List[ChunkData]:
    if not input_data:
        return []
    chunks = []
    for retrieved_data in input_data:
        if isinstance(retrieved_data, ChunkData):
            chunks.append(retrieved_data)
    return chunks


def get_all_docs_by_id(doc_ids: List[Tuple[str, float]], graph_api, schema_helper):
    """
    Retrieve a list of documents based on their IDs.

    Parameters:
    - queries (list of str): The query string for text matching.
    - doc_ids (list): A list of document IDs to retrieve documents.
    - top_k (int): The maximum number of documents to return.

    Returns:
    - list: A list of matched documents.
    """
    matched_docs = []
    hits_docs = []

    def process_get_doc_id(doc_id):
        doc_score = doc_id[1]
        doc_id = doc_id[0]
        try:
            node = graph_api.get_entity_prop_by_id(
                label=schema_helper.get_label_within_prefix(CHUNK_TYPE),
                biz_id=doc_id,
            )
            node_dict = dict(node.items())
            return doc_id, ChunkData(
                content=node_dict["content"].replace("_split_0", ""),
                title=node_dict["name"].replace("_split_0", ""),
                chunk_id=doc_id,
                score=doc_score,
                properties=node_dict,
            )
        except Exception as e:
            logger.warning(f"{doc_id} get_entity_prop_by_id failed: {e}", exc_info=True)
            return doc_id, None

    doc_maps = {}
    with ThreadPoolExecutor() as executor:
        doc_res = list(executor.map(process_get_doc_id, doc_ids))
        for d in doc_res:
            if d[1]:
                doc_maps[d[0]] = d[1]
    for doc_id in doc_ids:
        matched_docs.append(doc_maps[doc_id[0]])

    return matched_docs
