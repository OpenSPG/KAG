import logging
import numpy as np

from typing import List, Dict

from kag.common.conf import KAG_PROJECT_CONF, KAG_CONFIG
from kag.interface import ToolABC, VectorizeModelABC, LLMClient
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.tools.graph_api.graph_api_abc import GraphApiABC
from kag.solver.tools.search_api.search_api_abc import SearchApiABC
from kag.tools.algorithm_tool.chunk_retriever.text_chunk_retriever import TextChunkRetriever
from kag.tools.algorithm_tool.chunk_retriever.vector_chunk_retriever import VectorChunkRetriever
from kag.tools.algorithm_tool.graph_retriever.entity_linking import EntityLinking
from kag.tools.algorithm_tool.ner import Ner
from knext.schema.client import CHUNK_TYPE

logger = logging.getLogger()

@ToolABC.register("ppr_chunk_retriever")
class PprChunkRetriever(ToolABC):
    def __init__(self,
                 llm_module: LLMClient,
                 vectorize_model: VectorizeModelABC = None,
                 graph_api: GraphApiABC = None,
                 search_api: SearchApiABC = None,
                 pagerank_threshold: float = 0.8,
                 match_threshold: float = 0.9,
                 pagerank_weight: float = 0.5,
                 ner: Ner = None,
                 el: EntityLinking = None,
                 text_chunk_retriever: TextChunkRetriever = None,
                 vector_chunk_retriever: VectorChunkRetriever = None):
        super().__init__()
        self.schema: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
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
            KAG_CONFIG.all_config["vectorize_model"]
        )
        self.text_similarity = TextSimilarity(vectorize_model)

        self.ner = ner or Ner(llm_module=llm_module)
        self.el = el or EntityLinking(vectorize_model=vectorize_model, graph_api=graph_api, search_api=search_api, recognition_threshold=match_threshold)
        self.pagerank_threshold = pagerank_threshold
        self.text_chunk_retriever = text_chunk_retriever or TextChunkRetriever(search_api=search_api)
        self.vector_chunk_retriever = vector_chunk_retriever or VectorChunkRetriever(vectorize_model=vectorize_model, search_api=search_api)
        self.match_threshold = match_threshold
        self.pagerank_weight = pagerank_weight

    def calculate_pagerank_scores(self, start_nodes: List[EntityData]):
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
                target_type = self.schema.get_label_within_prefix(CHUNK_TYPE)
                start_node_set = []
                for s in start_nodes:
                    if s.type == target_type or not s.name or not s.type:
                        continue
                    start_node_set.append({
                        "name": s.name,
                        "type": s.type,
                    })
                scores = self.graph_api.calculate_pagerank_scores(
                    self.schema.get_label_within_prefix(CHUNK_TYPE), start_node_set
                )
            except Exception as e:
                logger.error(
                    f"run calculate_pagerank_scores failed, info: {e}, start_nodes: {start_nodes}",
                    exc_info=True,
                )
        return scores


    def calculate_combined_scores(
        self, sim_scores: Dict[str, float], pagerank_scores: Dict[str, float]
    ):
        """
        Calculate and return the combined scores that integrate both similarity scores and PageRank scores.

        Parameters:
        sim_scores (Dict[str, float]): A dictionary containing similarity scores, where keys are identifiers and values are scores.
        pagerank_scores (Dict[str, float]): A dictionary containing PageRank scores, where keys are identifiers and values are scores.

        Returns:
        Dict[str, float]: A dictionary containing the combined scores, where keys are identifiers and values are the combined scores.
        """

        def min_max_normalize(x):
            if len(x) == 0:
                return []
            if np.max(x) - np.min(x) > 0:
                return (x - np.min(x)) / (np.max(x) - np.min(x))
            else:
                return x - np.min(x)

        all_keys = set(pagerank_scores.keys()).union(set(sim_scores.keys()))
        for key in all_keys:
            sim_scores.setdefault(key, 0.0)
            pagerank_scores.setdefault(key, 0.0)
        sim_scores = dict(
            zip(
                sim_scores.keys(),
                min_max_normalize(np.array(list(sim_scores.values()))),
            )
        )
        pagerank_scores = dict(
            zip(
                pagerank_scores.keys(),
                min_max_normalize(np.array(list(pagerank_scores.values()))),
            )
        )
        combined_scores = dict()
        for key in pagerank_scores.keys():
            combined_scores[key] = (
                sim_scores[key] * (1 - self.pagerank_weight)
                + pagerank_scores[key] * self.pagerank_weight
            )
        return combined_scores

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
        hits_docs = set()
        counter = 0
        for doc_id in doc_ids:
            if counter == top_k:
                break
            if isinstance(doc_id, tuple):
                doc_score = doc_id[1]
                doc_id = doc_id[0]
            else:
                doc_score = doc_ids[doc_id]
            if doc_score == 0.0:
                continue
            counter += 1
            try:
                node = self.graph_api.get_entity_prop_by_id(
                    label=self.schema.get_label_within_prefix(CHUNK_TYPE),
                    biz_id=doc_id,
                )
                node_dict = dict(node.items())
                matched_docs.append(
                    f"#{node_dict['name']}#{node_dict['content']}#{doc_score}"
                )
                hits_docs.add(node_dict["name"])
            except Exception as e:
                logger.warning(
                    f"{doc_id} get_entity_prop_by_id failed: {e}", exc_info=True
                )
        query = "\n".join(queries)
        try:
            text_matched = self.search_api.search_text(
                query, [self.schema.get_label_within_prefix(CHUNK_TYPE)], topk=1
            )
            if text_matched:
                for item in text_matched:
                    title = item["node"]["name"]
                    if title not in hits_docs:
                        if len(matched_docs) > 0:
                            matched_docs.pop()
                        else:
                            logger.warning(f"{query} matched docs is empty")
                        matched_docs.append(
                            f'#{item["node"]["name"]}#{item["node"]["content"]}#{item["score"]}'
                        )
                        break
        except Exception as e:
            logger.warning(f"{query} query chunk failed: {e}", exc_info=True)
        logger.debug(f"matched_docs: {matched_docs}")
        return matched_docs
    def invoke(self, queries: List[str], start_entities: List[EntityData], top_k: int, **kwargs)->List[str]:
        chunk_nums = top_k * 20
        matched_entities = start_entities
        if start_entities is None:
            matched_entities = []
        for query in queries:
            candidate_entities = self.ner.invoke(query, **kwargs)
            for candidate_entity in candidate_entities:
                el_res = self.el.invoke(query=query, name=candidate_entity.get_mention_name(), type_name=candidate_entity.get_entity_first_type_or_un_std(), top_k=1)
                matched_entities.extend(el_res)

        if len(matched_entities):
            pagerank_scores = self.calculate_pagerank_scores(matched_entities)
        else:
            pagerank_scores = []

        try:
            matched_scores = [k.score for k in matched_entities]
        except Exception as e:
            matched_scores = []
            logger.error(f"mathematics error: {e}")

        if matched_entities and np.min(matched_scores) > self.pagerank_threshold:
            combined_scores = pagerank_scores
        else:
            sim_scores = {}
            queries = queries[1:]
            for query in queries:
                query_sim_scores = self.vector_chunk_retriever.invoke(query, chunk_nums)
                for doc_id, node in query_sim_scores.items():
                    score = node['score']
                    if doc_id not in sim_scores:
                        sim_scores[doc_id] = score
                    elif score > sim_scores[doc_id]:
                        sim_scores[doc_id] = score
            if not matched_entities:
                combined_scores = sim_scores
            else:
                combined_scores = self.calculate_combined_scores(
                    sim_scores, pagerank_scores
                )
        sorted_scores = sorted(
            combined_scores.items(), key=lambda item: item[1], reverse=True
        )

        return self.get_all_docs_by_id(queries, sorted_scores, top_k)


    def schema(self):
        return {
            "name": "ppr_chunk_retriever",
            "description": "Retrieve document chunks using Personalized PageRank algorithm with knowledge graph entities",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for context retrieval"
                    },
                    "start_entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "Entity ID in knowledge graph"},
                                "type": {"type": "string", "description": "Entity type category"},
                                "name": {"type": "string", "description": "Canonical entity name"},
                                "score": {"type": "string", "description": "The weight of this entity"}
                            },
                            "required": ["id", "name", "score"]
                        },
                        "description": "Seed entities for personalized PageRank calculation"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top-ranked chunks to return",
                        "default": 5,
                        "minimum": 1
                    }
                },
                "required": ["query", "start_entities"]
            }
        }
