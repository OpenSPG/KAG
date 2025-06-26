import logging
import time
from concurrent.futures import ThreadPoolExecutor

from typing import List

from kag.common.utils import get_recall_node_label

from kag.interface import (
    RetrieverABC,
    VectorizeModelABC,
    ChunkData,
    LLMClient,
    SchemaUtils,
    EntityData,
    RetrieverOutput,
)
from kag.common.config import LogicFormConfiguration
from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
from kag.common.tools.search_api.search_api_abc import SearchApiABC

from kag.common.tools.algorithm_tool.ner import Ner
from knext.schema.client import CHUNK_TYPE


logger = logging.getLogger()


@RetrieverABC.register("ppr_chunk_retriever")
class PprChunkRetriever(RetrieverABC):
    def __init__(
        self,
        llm_client: LLMClient,
        vectorize_model: VectorizeModelABC = None,
        graph_api: GraphApiABC = None,
        search_api: SearchApiABC = None,
        match_threshold: float = 0.6,
        pagerank_weight: float = 0.5,
        ner: Ner = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": self.kag_project_config.project_id,
                    "KAG_PROJECT_HOST_ADDR": self.kag_project_config.host_addr,
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
            self.kag_config.all_config["vectorize_model"]
        )

        self.ner = ner or Ner(llm_module=llm_client, **kwargs)
        self.match_threshold = match_threshold
        self.pagerank_weight = pagerank_weight

    def calculate_pagerank_scores(self, start_nodes: List[EntityData], top_k):
        """
        Calculate and retrieve PageRank scores for the given starting nodes.

        Parameters:
        start_nodes (list): A list containing document fragment IDs to be used as starting nodes for the PageRank algorithm.

        Returns:
        ppr_doc_scores (dict): A dictionary containing each document fragment ID and its corresponding PageRank score.

        This method uses the PageRank algorithm in the graph store to compute scores for document fragments. If `start_nodes` is empty,
        it returns an empty dictionary. Otherwise, it attempts to retrieve PageRank scores from the graph store and converts the result
        into a dictionary format where keys are document fragment IDs and values are their respective PageRank scores. Any exceptions,
        such as failures in running `run_pagerank_igraph_chunk`, are logged.
        """
        scores = dict()
        if len(start_nodes) != 0:
            try:
                target_type = self.schema_helper.get_label_within_prefix(CHUNK_TYPE)
                start_node_set = []
                for s in start_nodes:
                    if s.type == target_type or not s.name or not s.type:
                        continue
                    start_node_set.append(
                        {
                            "id": s.biz_id,
                            "name": s.name,
                            "type": s.type,
                        }
                    )
                if len(start_node_set) == 0:
                    return scores
                scores = self.graph_api.calculate_pagerank_scores(
                    self.schema_helper.get_label_within_prefix(CHUNK_TYPE),
                    start_node_set,
                    top_k=top_k,
                )
            except Exception as e:
                logger.error(
                    f"run calculate_pagerank_scores failed, info: {e}, start_nodes: {start_nodes}",
                    exc_info=True,
                )
        return scores

    def get_all_docs_by_id(self, queries: List[str], doc_ids: list, top_k: int):
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
        start_time = time.time()

        def process_get_doc_id(doc_id):
            if isinstance(doc_id, tuple):
                doc_score = doc_id[1]
                doc_id = doc_id[0]
            else:
                doc_score = doc_ids[doc_id]
            try:
                node = self.graph_api.get_entity_prop_by_id(
                    label=self.schema_helper.get_label_within_prefix(CHUNK_TYPE),
                    biz_id=doc_id,
                )
                node_dict = dict(node.items())
                return doc_id, ChunkData(
                    content=node_dict.get("content", "").replace("_split_0", ""),
                    title=node_dict["name"].replace("_split_0", ""),
                    chunk_id=doc_id,
                    score=doc_score,
                    properties=node_dict,
                )
            except Exception as e:
                logger.warning(
                    f"{doc_id} get_entity_prop_by_id failed: {e}", exc_info=True
                )
                return None

        limit_doc_ids = doc_ids[:top_k]
        doc_maps = {}
        with ThreadPoolExecutor(max_workers=20) as executor:
            doc_res = list(executor.map(process_get_doc_id, limit_doc_ids))
            for d in doc_res:
                if d[1]:
                    doc_maps[d[0]] = d[1]
        for doc_id in limit_doc_ids:
            matched_docs.append(doc_maps[doc_id[0]])
            hits_docs.append(doc_maps[doc_id[0]].chunk_id)
        logger.info(
            f"{queries} get_all_docs_by_id cost {time.time() - start_time}s, recall num = {len(doc_ids)} "
        )
        query = "\n".join(queries)
        start_time = time.time()
        try:
            text_matched = self.search_api.search_text(
                query, [self.schema_helper.get_label_within_prefix(CHUNK_TYPE)], topk=1
            )
            if text_matched:
                for item in text_matched:
                    if item["node"]["id"] not in hits_docs:
                        if len(matched_docs) > 0:
                            matched_docs.pop()
                        else:
                            logger.warning(f"{query} matched docs is empty")
                        matched_docs.append(
                            ChunkData(
                                content=item["node"].get("content", ""),
                                title=item["node"]["name"],
                                chunk_id=item["node"]["id"],
                                score=item["score"],
                                properties=item["node"],
                            )
                        )
                        break
        except Exception as e:
            logger.warning(f"{query} query chunk failed: {e}", exc_info=True)
        logger.info(
            f"{queries} get_all_docs_by_id search text cost {time.time() - start_time}s"
        )

        return matched_docs

    def linking_matched_entities(self, query: str, **kwargs):
        start_entities = kwargs.get("start_entities", [])
        if start_entities:
            return start_entities
        matched_entities = []
        ner_maps = {}
        ner_start_time = time.time()
        start_entity_maps = {}
        candidate_entities = self.ner.invoke(query, **kwargs)
        for candidate_entity in candidate_entities:
            query_type = candidate_entity.get_entity_first_type_or_un_std()

            ner_id = f"{candidate_entity.entity_name}_{query_type}"
            if ner_id not in ner_maps:
                ner_maps[ner_id] = {
                    "candidate": candidate_entity,
                    "query": query,
                    "query_type": query_type,
                }
        logger.info(
            f"NER completed in {time.time() - ner_start_time:.2f} seconds. Found {len(ner_maps)} unique entities."
        )

        logger.info(
            f"Performing entity linking (EL) for {len(ner_maps)} candidate entities."
        )

        def process_entity(k, data):
            """Process a single entity in parallel."""
            mention = data["candidate"].entity_name

            query_entity_vector = self.vectorize_model.vectorize(mention)

            top_entities = self.search_api.search_vector(
                label="Entity",
                property_key="name",
                query_vector=query_entity_vector,
                topk=1,
            )
            for top_entity in top_entities:
                score = top_entity["score"]
                if score > 0.7:
                    recalled_entity = EntityData()
                    recalled_entity.score = top_entity["score"]
                    recalled_entity.biz_id = top_entity["node"]["id"]
                    recalled_entity.name = top_entity["node"]["name"]
                    recalled_entity.type = get_recall_node_label(
                        top_entity["node"]["__labels__"]
                    )
                    return [recalled_entity]
            return []

        # Use ThreadPoolExecutor to parallelize EL processing
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(
                executor.map(
                    lambda item: process_entity(item[0], item[1]), ner_maps.items()
                )
            )

        # Flatten the results and extend matched_entities
        for result in results:
            if result:
                for r in result:
                    e_id = f"{r.biz_id}_{r.type}"
                    if e_id in start_entity_maps:
                        continue
                    start_entity_maps[e_id] = r
                    matched_entities.append(r)
        return matched_entities

    def invoke(self, task, **kwargs) -> RetrieverOutput:
        el_start_time = time.time()
        top_k = kwargs.get("top_k", self.top_k)
        query = task.arguments["query"]
        matched_entities = self.linking_matched_entities(query, **kwargs)

        logger.info(
            f"Entity linking completed in {time.time() - el_start_time:.2f} seconds. Found {len(matched_entities)} unique entities."
        )

        pagerank_start_time = time.time()
        if len(matched_entities):
            pagerank_res = self.calculate_pagerank_scores(matched_entities, top_k=top_k)
        else:
            pagerank_res = {}
        logger.info(
            f"PageRank calculation {query} completed in {time.time() - pagerank_start_time:.2f} seconds."
        )
        pagerank_scores = {}
        is_need_get_doc = False
        for k, v in pagerank_res.items():
            if isinstance(v, float):
                pagerank_scores[k] = v
                is_need_get_doc = True
            else:
                pagerank_scores[k] = v["score"]

        sorted_scores = sorted(
            pagerank_scores.items(), key=lambda item: item[1], reverse=True
        )
        if is_need_get_doc:
            matched_docs = self.get_all_docs_by_id([query], sorted_scores, top_k)
        else:
            matched_docs = []
            for doc_id, score in sorted_scores:
                node = pagerank_res[doc_id]["node"]
                matched_docs.append(
                    ChunkData(
                        content=node["content"].replace("_split_0", ""),
                        title=node["name"].replace("_split_0", ""),
                        chunk_id=doc_id,
                        score=score,
                        properties=node,
                    )
                )
        return RetrieverOutput(retriever_method=self.name, chunks=matched_docs)

    def schema(self):
        return {
            "name": "ppr_chunk_retriever",
            "description": "Retrieve document chunks using Personalized PageRank algorithm with knowledge graph entities",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for context retrieval",
                    },
                },
                "required": ["query"],
            },
        }
