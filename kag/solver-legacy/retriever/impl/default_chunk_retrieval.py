# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.
import knext.common.cache
from kag.interface import PromptABC, VectorizeModelABC
from tenacity import retry, stop_after_attempt

from kag.interface import VectorizeModelABC as Vectorizer
from kag.interface import LLMClient
from typing import List, Dict, Optional

import numpy as np
import logging

from kag.solver.tools.graph_api.graph_api_abc import GraphApiABC
from kag.solver.tools.search_api.search_api_abc import SearchApiABC
from knext.schema.client import CHUNK_TYPE, OTHER_TYPE
from kag.common.utils import processing_phrases
from kag.common.conf import KAG_CONFIG
from kag.solver.retriever.chunk_retriever import ChunkRetriever
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData, RelationData
from kag.solver.logic.core_modules.common.text_sim_by_vector import (
    TextSimilarity,
    cosine_similarity,
)
from kag.solver.utils import init_prompt_with_fallback

logger = logging.getLogger(__name__)

ner_cache = knext.common.cache.LinkCache(maxsize=100, ttl=300)
query_sim_doc_cache = knext.common.cache.LinkCache(maxsize=100, ttl=300)


@ChunkRetriever.register("kag")
class KAGRetriever(ChunkRetriever):
    """
    KAGRetriever class for retrieving and processing knowledge graph data from a graph database.

    this retriever references the implementation of Hippoag for the combination of dpr & ppr, developer can define your Retriever

    Parameters:
    - project_id (str, optional): Project ID to load specific project configurations.
    - host_addr (str, optional): host addr to load specific server addr configurations.
    """

    def __init__(
        self,
        ner_prompt: PromptABC = None,
        std_prompt: PromptABC = None,
        pagerank_threshold: float = 0.9,
        match_threshold: float = 0.9,
        pagerank_weight: float = 0.5,
        recall_num: int = 10,
        rerank_topk: int = 10,
        reranker_model_path: str = None,
        vectorize_model: Vectorizer = None,
        graph_api: GraphApiABC = None,
        search_api: SearchApiABC = None,
        llm_client: LLMClient = None,
        **kwargs,
    ):
        super().__init__(
            recall_num, rerank_topk, graph_api, search_api, llm_client, **kwargs
        )
        if vectorize_model is None:
            vectorize_model = Vectorizer.from_config(
                KAG_CONFIG.all_config["vectorize_model"]
            )
        self.vectorize_model = vectorize_model
        if ner_prompt is None:
            ner_prompt = init_prompt_with_fallback("question_ner", self.biz_scene)

        self.ner_prompt = ner_prompt
        if std_prompt is None:
            std_prompt = init_prompt_with_fallback("std", self.biz_scene)
        self.std_prompt = std_prompt

        self.pagerank_threshold = pagerank_threshold
        self.match_threshold = match_threshold
        self.pagerank_weight = pagerank_weight

        self.reranker_model_path = reranker_model_path
        if self.reranker_model_path:
            from kag.common.reranker.reranker import BGEReranker

            self.reranker = BGEReranker(self.reranker_model_path, use_fp16=True)
        else:
            self.reranker = None

        self.with_semantic = True

    @retry(stop=stop_after_attempt(3))
    def named_entity_recognition(self, query: str):
        """
        Perform named entity recognition.

        This method invokes the pre-configured service client (self.llm) to process the input query,
        using the named entity recognition (NER) prompt (self.ner_prompt).

        Parameters:
        query (str): The text input provided by the user or system for named entity recognition.

        Returns:
        The result returned by the service client, with the type and format depending on the used service.
        """
        return self.llm_module.invoke({"input": query}, self.ner_prompt)

    @retry(stop=stop_after_attempt(3))
    def named_entity_standardization(self, query: str, entities: List[Dict]):
        """
        Entity standardization function.

        This function calls a remote service to process the input query and named entities,
        standardizing the entities. This is useful for unifying different representations of the same entity in text,
        improving the performance of natural language processing tasks.

        Parameters:
        - query: A string containing the query with named entities.
        - entities: A list of dictionaries, each containing information about named entities.

        Returns:
        - The result of the remote service call, typically standardized named entity information.
        """
        return self.llm_module.invoke(
            {"input": query, "named_entities": entities}, self.std_prompt
        )

    @staticmethod
    def append_official_name(
        source_entities: List[Dict], entities_with_official_name: List[Dict]
    ):
        """
        Appends official names to entities.

        Parameters:
        source_entities (List[Dict]): A list of source entities.
        entities_with_official_name (List[Dict]): A list of entities with official names.

        """
        tmp_dict = {}
        for tmp_entity in entities_with_official_name:
            name = tmp_entity["name"]
            category = tmp_entity["category"]
            official_name = tmp_entity["official_name"]
            key = f"{category}{name}"
            tmp_dict[key] = official_name

        for tmp_entity in source_entities:
            name = tmp_entity["name"]
            category = tmp_entity["category"]
            key = f"{category}{name}"
            if key in tmp_dict:
                official_name = tmp_dict[key]
                tmp_entity["official_name"] = official_name

    def calculate_sim_scores(self, query: str, doc_nums: int):
        """
        Calculate the vector similarity scores between a query and document chunks.

        Parameters:
        query (str): The user's query text.
        doc_nums (int): The number of document chunks to return.

        Returns:
        dict: A dictionary with keys as document chunk IDs and values as the vector similarity scores.
        """
        try:
            scores = query_sim_doc_cache.get(query)
            if scores:
                return scores
            query_vector = self.vectorize_model.vectorize(query)
            top_k = self.search_api.search_vector(
                label=self.schema.get_label_within_prefix(CHUNK_TYPE),
                property_key="content",
                query_vector=query_vector,
                topk=doc_nums,
            )
            scores = {item["node"]["id"]: item["score"] for item in top_k}
            query_sim_doc_cache.put(query, scores)
        except Exception as e:
            scores = dict()
            logger.error(f"run calculate_sim_scores failed, info: {e}", exc_info=True)
        return scores

    def calculate_pagerank_scores(self, start_nodes: List[Dict]):
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
                    if s["type"] == target_type:
                        continue
                    start_node_set.append(s)
                scores = self.graph_api.calculate_pagerank_scores(
                    self.schema.get_label_within_prefix(CHUNK_TYPE), start_node_set
                )
            except Exception as e:
                logger.error(
                    f"run calculate_pagerank_scores failed, info: {e}, start_nodes: {start_nodes}",
                    exc_info=True,
                )
        return scores

    def match_entities(self, queries: Dict[str, str], top_k: int = 1):
        """
        Match entities based on the provided queries.

        :param queries: A dictionary containing keywords and their labels.
        :param top_k: The number of top results to return. Default is 1.
        :return: A tuple containing a list of matched entities and their scores.
        """
        matched_entities = []
        for query, query_type in queries.items():
            query = processing_phrases(query)
            if query_type not in self.schema.node_en_zh.keys():
                query_type = self.schema.get_label_within_prefix(OTHER_TYPE)
            else:
                query_type = self.schema.get_label_within_prefix(query_type)
            typed_nodes = self.search_api.search_vector(
                label=query_type,
                property_key="name",
                query_vector=self.vectorize_model.vectorize(query),
                topk=top_k,
            )
            if query_type != self.schema.get_label_within_prefix(OTHER_TYPE):
                nontyped_nodes = self.search_api.search_vector(
                    label=self.schema.get_label_within_prefix(OTHER_TYPE),
                    property_key="name",
                    query_vector=self.vectorize_model.vectorize(query),
                    topk=top_k,
                )
            else:
                nontyped_nodes = typed_nodes

            if len(typed_nodes) == 0 and len(nontyped_nodes) != 0:
                matched_entities.append(
                    {
                        "name": nontyped_nodes[0]["node"]["name"],
                        "type": self.schema.get_label_within_prefix(OTHER_TYPE),
                        "score": nontyped_nodes[0]["score"],
                    }
                )
            elif len(typed_nodes) != 0 and len(nontyped_nodes) != 0:
                if typed_nodes[0]["score"] > 0.8:
                    matched_entities.append(
                        {
                            "name": typed_nodes[0]["node"]["name"],
                            "type": query_type,
                            "score": typed_nodes[0]["score"],
                        }
                    )
                else:
                    matched_entities.append(
                        {
                            "name": nontyped_nodes[0]["node"]["name"],
                            "type": self.schema.get_label_within_prefix(OTHER_TYPE),
                            "score": nontyped_nodes[0]["score"],
                        }
                    )
                    matched_entities.append(
                        {
                            "name": typed_nodes[0]["node"]["name"],
                            "type": query_type,
                            "score": typed_nodes[0]["score"],
                        }
                    )
            elif len(typed_nodes) != 0 and len(nontyped_nodes) == 0:
                if typed_nodes[0]["score"] > 0.8:
                    matched_entities.append(
                        {
                            "name": typed_nodes[0]["node"]["name"],
                            "type": query_type,
                            "score": typed_nodes[0]["score"],
                        }
                    )

        if not matched_entities:
            logger.info(f"No entities matched for {queries}")
        return matched_entities

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

    def _add_extra_entity_from_spo(
        self, matched_entities: Dict, retrieved_spo: List[RelationData]
    ):
        all_related_entities = []
        if retrieved_spo:
            for spo in retrieved_spo:
                if spo.from_entity.type not in ["Text", "attribute"]:
                    all_related_entities.append(spo.from_entity)
                if spo.end_entity.type not in ["Text", "attribute"]:
                    all_related_entities.append(spo.end_entity)
            all_related_entities = list(set(all_related_entities))

        if len(all_related_entities) == 0:
            return matched_entities.values()

        ner_cands = matched_entities

        def convert_entity_data_to_ppr_cand(related_entities: List[EntityData]):
            ret_ppr_candis = {}
            for e in related_entities:
                k = f"{e.name}_{e.type}"
                ret_ppr_candis[k] = {"name": e.name, "type": e.type, "score": e.score}
            return ret_ppr_candis

        kg_cands = convert_entity_data_to_ppr_cand(all_related_entities)
        for k, v in ner_cands.items():
            if k in kg_cands.keys():
                if v["score"] > kg_cands[k]["score"]:
                    kg_cands[k]["score"] = v["score"]
            else:
                kg_cands[k] = v

        matched_entities = []
        matched_entities_scores = []
        for _, v in kg_cands.items():
            matched_entities.append(v)
            matched_entities_scores.append(v["score"])
        return matched_entities

    def _parse_ner_list(self, query):
        ner_list = []
        try:
            ner_list = ner_cache.get(query)
            if ner_list:
                return ner_list
            ner_list = self.named_entity_recognition(query)
            if self.with_semantic:
                std_ner_list = self.named_entity_standardization(query, ner_list)
                self.append_official_name(ner_list, std_ner_list)
            ner_cache.put(query, ner_list)
        except Exception as e:
            if not ner_list:
                ner_list = []
            logger.warning(f"_parse_ner_list {query} failed {e}", exc_info=True)
        return ner_list

    def recall_docs(
        self,
        queries: List[str],
        retrieved_spo: Optional[List[RelationData]] = None,
        **kwargs,
    ) -> List[str]:
        """
        Recall relevant documents based on the query string.

        Parameters:
        - query (str): The user's query string.
        - top_k (int, optional): The number of documents to return, default is 5.

        Keyword Arguments:
        - kwargs: Additional keyword arguments.

        Returns:
        - list: A list containing the top_k most relevant documents.
        """
        chunk_nums = self.recall_num * 20
        if chunk_nums == 0:
            return []
        matched_entities_map = {}
        for query in queries:
            entities = {}
            assert isinstance(query, str), "Query must be a string"
            ner_list = self._parse_ner_list(query)
            for item in ner_list:
                entity = item.get("name", "")
                category = item.get("category", "")
                official_name = item.get("official_name", "")
                if not entity or not (category or official_name):
                    continue
                if category.lower() in ["works", "person", "other"]:
                    entities[entity] = category
                else:
                    entities[entity] = official_name or category

            cur_matched = self.match_entities(entities)
            for matched_entity in cur_matched:
                key = f"{matched_entity['name']}_{matched_entity['type']}"
                if (
                    key not in matched_entities_map
                    or matched_entity["score"] > matched_entities_map[key]["score"]
                ):
                    matched_entities_map[key] = matched_entity

        matched_entities = self._add_extra_entity_from_spo(
            retrieved_spo=retrieved_spo, matched_entities=matched_entities_map
        )
        try:
            matched_scores = [k["score"] for k in matched_entities]
        except Exception as e:
            logger.error(f"mathematics error: {e}")
        if len(matched_entities):
            pagerank_scores = self.calculate_pagerank_scores(matched_entities)
        else:
            pagerank_scores = []

        if matched_entities and np.min(matched_scores) > self.pagerank_threshold:
            combined_scores = pagerank_scores
        else:
            sim_scores = {}
            queries = queries[1:]
            for query in queries:
                query_sim_scores = self.calculate_sim_scores(query, chunk_nums)
                for doc_id, score in query_sim_scores.items():
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
        logger.debug(f"sorted_scores: {sorted_scores}")

        return self.get_all_docs_by_id(queries, sorted_scores, self.recall_num)

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

    def rerank_docs(self, queries: List[str], passages: List[str]):
        """
        Re-ranks the given passages based on the provided queries.

        Parameters:
        - queries (List[str]): A list of queries.
        - passages (List[str]): A list of passages.

        Returns:
        - List[str]: A re-ranked list of passages.
        """
        if self.reranker is None:
            return passages
        return self.reranker.rerank(queries, passages)


@ChunkRetriever.register("default_chunk_retriever")
class DefaultChunkRetriever(KAGRetriever):
    def __init__(
        self,
        ner_prompt: PromptABC = None,
        std_prompt: PromptABC = None,
        pagerank_threshold: float = 0.9,
        match_threshold: float = 0.9,
        pagerank_weight: float = 0.5,
        recall_num: int = 10,
        rerank_topk: int = 10,
        reranker_model_path: str = None,
        vectorize_model: VectorizeModelABC = None,
        graph_api: GraphApiABC = None,
        search_api: SearchApiABC = None,
        llm_client: LLMClient = None,
        **kwargs,
    ):
        super().__init__(
            ner_prompt,
            std_prompt,
            pagerank_threshold,
            match_threshold,
            pagerank_weight,
            recall_num,
            rerank_topk,
            reranker_model_path,
            vectorize_model,
            graph_api,
            search_api,
            llm_client,
            **kwargs,
        )
        self.text_sim = TextSimilarity(vectorizer=self.vectorize_model)

    def rerank_docs(self, queries: List[str], passages: List[str]):
        if not isinstance(queries, list):
            queries = [queries]
        if len(passages) == 0:
            return []
        queries = list(set(queries))
        rank_scores = np.array([1 / (1 + i) for i in range(len(passages))])
        passage_scores = np.zeros(len(passages)) + rank_scores
        passages_embs = self.text_sim.sentence_encode(passages, is_cached=True)

        for query in queries:
            query_emb = self.text_sim.sentence_encode(query)
            scores = [
                cosine_similarity(np.array(query_emb), np.array(passage_emb))
                for passage_emb in passages_embs
            ]
            sorted_idx = np.argsort(-np.array(scores))
            for rank, passage_id in enumerate(sorted_idx):
                passage_scores[passage_id] += rank_scores[rank]

        merged_sorted_idx = np.argsort(-passage_scores)

        new_passages = [passages[x] for x in merged_sorted_idx]
        return new_passages[: self.rerank_topk]
