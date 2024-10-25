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

import os
from tenacity import retry, stop_after_attempt

from kag.common.base.prompt_op import PromptOp
from kag.common.vectorizer import Vectorizer
from knext.graph_algo.client import GraphAlgoClient
from kag.interface.retriever.chunk_retriever_abc import ChunkRetrieverABC
from typing import List, Dict

import numpy as np
import logging

from knext.reasoner.client import ReasonerClient
from knext.schema.client import CHUNK_TYPE, OTHER_TYPE
from knext.project.client import ProjectClient
from kag.common.utils import processing_phrases
from knext.search.client import SearchClient
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.config import LogicFormConfiguration

logger = logging.getLogger(__name__)


class DefaultRetriever(ChunkRetrieverABC):
    """
    KAGRetriever class for retrieving and processing knowledge graph data from a graph database.

    this retriever references the implementation of Hippoag for the combination of dpr & ppr, developer can define your Retriever

    Parameters:
    - project_id (str, optional): Project ID to load specific project configurations.
    - host_addr (str, optional): host addr to load specific server addr configurations.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.schema_util = SchemaUtils(LogicFormConfiguration(kwargs))

        self._init_search()

        self.ner_prompt = PromptOp.load(self.biz_scene, "question_ner")(language=self.language, project_id=self.project_id)
        self.std_prompt = PromptOp.load(self.biz_scene, "std")(language=self.language)

        self.pagerank_threshold = 0.9
        self.match_threshold = 0.8
        self.pagerank_weight = 0.5

        self.reranker_model_path = os.getenv("KAG_RETRIEVER_RERANKER_MODEL_PATH")
        if self.reranker_model_path:
            from kag.common.reranker.reranker import BGEReranker
            self.reranker = BGEReranker(self.reranker_model_path, use_fp16=True)
        else:
            self.reranker = None

        self.with_semantic = True

    def _init_search(self):
        self.sc: SearchClient = SearchClient(self.host_addr, self.project_id)
        vectorizer_config = eval(os.getenv("KAG_VECTORIZER", "{}"))
        if self.host_addr and self.project_id:
            config = ProjectClient(host_addr=self.host_addr, project_id=self.project_id).get_config(self.project_id)
            vectorizer_config.update(config.get("vectorizer", {}))

        self.vectorizer = Vectorizer.from_config(
            vectorizer_config
        )
        self.reason: ReasonerClient = ReasonerClient(self.host_addr, self.project_id)
        self.graph_algo = GraphAlgoClient(self.host_addr, self.project_id)




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
    def append_official_name(source_entities: List[Dict], entities_with_official_name: List[Dict]):
        """
        Appends official names to entities.

        Parameters:
        source_entities (List[Dict]): A list of source entities.
        entities_with_official_name (List[Dict]): A list of entities with official names.

        """
        tmp_dict = {}
        for tmp_entity in entities_with_official_name:
            name = tmp_entity["entity"]
            category = tmp_entity["category"]
            official_name = tmp_entity["official_name"]
            key = f"{category}{name}"
            tmp_dict[key] = official_name

        for tmp_entity in source_entities:
            name = tmp_entity["entity"]
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
        scores = dict()
        try:
            query_vector = self.vectorizer.vectorize(query)
            top_k = self.sc.search_vector(
                label=self.schema_util.get_label_within_prefix(CHUNK_TYPE),
                property_key="content",
                query_vector=query_vector,
                topk=doc_nums
            )
            scores = {item["node"]["id"]: item["score"] for item in top_k}
        except Exception as e:
            logger.error(
                f"run calculate_sim_scores failed, info: {e}", exc_info=True
            )
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
                scores = self.graph_algo.calculate_pagerank_scores(
                    self.schema_util.get_label_within_prefix(CHUNK_TYPE),
                    start_nodes
                )
            except Exception as e:
                logger.error(
                    f"run calculate_pagerank_scores failed, info: {e}, start_nodes: {start_nodes}", exc_info=True
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
        matched_entities_scores = []
        for query, query_type in queries.items():
            query = processing_phrases(query)
            if query_type not in self.schema_util.node_en_zh.keys():
                query_type = self.schema_util.get_label_within_prefix(OTHER_TYPE)
            typed_nodes = self.sc.search_vector(
                label=query_type,
                property_key="name",
                query_vector=self.vectorizer.vectorize(query),
                topk=top_k,
            )
            if query_type != self.schema_util.get_label_within_prefix(OTHER_TYPE):
                nontyped_nodes = self.sc.search_vector(
                    label=self.schema_util.get_label_within_prefix(OTHER_TYPE),
                    property_key="name",
                    query_vector=self.vectorizer.vectorize(query),
                    topk=top_k,
                )
            else:
                nontyped_nodes = typed_nodes

            if len(typed_nodes) == 0 and len(nontyped_nodes) != 0:
                matched_entities.append(
                    {"name": nontyped_nodes[0]["node"]["name"], "type": OTHER_TYPE}
                )
                matched_entities_scores.append(nontyped_nodes[0]["score"])
            elif len(typed_nodes) != 0 and len(nontyped_nodes) != 0:
                if typed_nodes[0]["score"] > 0.8:
                    matched_entities.append(
                        {"name": typed_nodes[0]["node"]["name"], "type": query_type}
                    )
                    matched_entities_scores.append(typed_nodes[0]["score"])
                else:
                    matched_entities.append(
                        {"name": nontyped_nodes[0]["node"]["name"], "type": OTHER_TYPE}
                    )
                    matched_entities_scores.append(nontyped_nodes[0]["score"])
                    matched_entities.append(
                        {"name": typed_nodes[0]["node"]["name"], "type": query_type}
                    )
                    matched_entities_scores.append(typed_nodes[0]["score"])
            elif len(typed_nodes) != 0 and len(nontyped_nodes) == 0:
                if typed_nodes[0]["score"] > 0.8:
                    matched_entities.append(
                        {"name": typed_nodes[0]["node"]["name"], "type": query_type}
                    )
                    matched_entities_scores.append(typed_nodes[0]["score"])

        if not matched_entities:
            logger.info(f"No entities matched for {queries}")
        return matched_entities, matched_entities_scores

    def calculate_combined_scores(self, sim_scores: Dict[str, float], pagerank_scores: Dict[str, float]):
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
        sim_scores = dict(zip(sim_scores.keys(), min_max_normalize(
            np.array(list(sim_scores.values()))
        )))
        pagerank_scores = dict(zip(pagerank_scores.keys(), min_max_normalize(
            np.array(list(pagerank_scores.values()))
        )))
        combined_scores = dict()
        for key in pagerank_scores.keys():
            combined_scores[key] = (sim_scores[key] * (1 - self.pagerank_weight) +
                                    pagerank_scores[key] * self.pagerank_weight
                                    )
        return combined_scores

    def recall_docs(self, query: str, top_k: int = 5, **kwargs):
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
        assert isinstance(query, str), "Query must be a string"

        chunk_nums = top_k * 20
        if chunk_nums == 0:
            return []

        ner_list = self.named_entity_recognition(query)
        print(ner_list)
        if self.with_semantic:
            std_ner_list = self.named_entity_standardization(query, ner_list)
            self.append_official_name(ner_list, std_ner_list)

        entities = {}
        for item in ner_list:
            entity = item.get("entity", "")
            category = item.get("category", "")
            official_name = item.get("official_name", "")
            if not entity or not (category or official_name):
                continue
            if category.lower() in ["works", "person", "other"]:
                entities[entity] = category
            else:
                entities[entity] = official_name or category

        sim_scores = self.calculate_sim_scores(query, chunk_nums)
        matched_entities, matched_scores = self.match_entities(entities)
        pagerank_scores = self.calculate_pagerank_scores(matched_entities)

        if not matched_entities:
            combined_scores = sim_scores
        elif matched_entities and np.min(matched_scores) > self.pagerank_threshold:
            combined_scores = pagerank_scores
        else:
            combined_scores = self.calculate_combined_scores(sim_scores, pagerank_scores)
        sorted_scores = sorted(
            combined_scores.items(), key=lambda item: item[1], reverse=True
        )
        logger.debug(f"sorted_scores: {sorted_scores}")

        return self.get_all_docs_by_id(query, sorted_scores, top_k)

    def get_all_docs_by_id(self, query: str, doc_ids: list, top_k: int):
        """
        Retrieve a list of documents based on their IDs.

        Parameters:
        - query (str): The query string for text matching.
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
            node = self.reason.query_node(label=self.schema_util.get_label_within_prefix(CHUNK_TYPE), id_value=doc_id)
            node_dict = dict(node.items())
            matched_docs.append(f"#{node_dict['name']}#{node_dict['content']}#{doc_score}")
            hits_docs.add(node_dict['name'])
        try:
            text_matched = self.sc.search_text(query, [self.schema_util.get_label_within_prefix(CHUNK_TYPE)], topk=1)
            if text_matched:
                for item in text_matched:
                    title = item["node"]["name"]
                    if title not in hits_docs:
                        if len(matched_docs) > 0:
                            matched_docs.pop()
                        else:
                            logger.warning(f"{query} matched docs is empty")
                        matched_docs.append(f'#{item["node"]["name"]}#{item["node"]["content"]}#{item["score"]}')
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
