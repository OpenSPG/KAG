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


from kag.interface import PromptABC, VectorizeModelABC
from tenacity import retry, stop_after_attempt

from kag.interface import VectorizeModelABC as Vectorizer
from knext.graph_algo.client import GraphAlgoClient

from typing import List, Dict

import numpy as np
import logging
import time
from knext.reasoner.client import ReasonerClient
from knext.schema.client import CHUNK_TYPE, OTHER_TYPE
from knext.search.client import SearchClient
from kag.interface import LLMClient
from kag.common.utils import processing_phrases
from kag.common.conf import KAG_CONFIG
from kag.solver.retriever.chunk_retriever import ChunkRetriever
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity

logger = logging.getLogger(__name__)


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
        reranker_model_path: str = None,
        llm_client: LLMClient = None,
        vectorize_model: Vectorizer = None,
        **kwargs,
    ):
        super().__init__(llm_client, **kwargs)

        self.schema_util = SchemaUtils(LogicFormConfiguration(kwargs))

        self._init_search()
        if vectorize_model is None:
            vectorize_model = Vectorizer.from_config(
                KAG_CONFIG.all_config["vectorize_model"]
            )
        self.vectorize_model = vectorize_model
        # self.ner_prompt = PromptOp.load(self.biz_scene, "question_ner")(
        #     language=self.language, project_id=self.project_id
        # )
        # self.std_prompt = PromptOp.load(self.biz_scene, "std")(language=self.language)
        if ner_prompt is None:
            ner_prompt = PromptABC.from_config(
                {"type": f"{self.biz_scene}_question_ner"}
            )
        self.ner_prompt = ner_prompt
        if std_prompt is None:
            std_prompt = PromptABC.from_config({"type": f"{self.biz_scene}_std"})
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

    def _init_search(self):
        self.sc: SearchClient = SearchClient(self.host_addr, self.project_id)
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
            query_vector = self.vectorize_model.vectorize(query)
            top_k = self.sc.search_vector(
                label=self.schema_util.get_label_within_prefix(CHUNK_TYPE),
                property_key="content",
                query_vector=query_vector,
                topk=doc_nums,
            )
            scores = {item["node"]["id"]: item["score"] for item in top_k}
        except Exception as e:
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
                scores = self.graph_algo.calculate_pagerank_scores(
                    self.schema_util.get_label_within_prefix(CHUNK_TYPE), start_nodes
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
        matched_entities_scores = []
        for query, query_type in queries.items():
            query = processing_phrases(query)
            if query_type not in self.schema_util.node_en_zh.keys():
                query_type = self.schema_util.get_label_within_prefix(OTHER_TYPE)
            typed_nodes = self.sc.search_vector(
                label=query_type,
                property_key="name",
                query_vector=self.vectorize_model.vectorize(query),
                topk=top_k,
            )
            if query_type != self.schema_util.get_label_within_prefix(OTHER_TYPE):
                nontyped_nodes = self.sc.search_vector(
                    label=self.schema_util.get_label_within_prefix(OTHER_TYPE),
                    property_key="name",
                    query_vector=self.vectorize_model.vectorize(query),
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
            combined_scores = self.calculate_combined_scores(
                sim_scores, pagerank_scores
            )
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
            node = self.reason.query_node(
                label=self.schema_util.get_label_within_prefix(CHUNK_TYPE),
                id_value=doc_id,
            )
            node_dict = dict(node.items())
            matched_docs.append(
                f"#{node_dict['name']}#{node_dict['content']}#{doc_score}"
            )
            hits_docs.add(node_dict["name"])
        try:
            text_matched = self.sc.search_text(
                query, [self.schema_util.get_label_within_prefix(CHUNK_TYPE)], topk=1
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


@ChunkRetriever.register("kag_lf")
class LFChunkRetriever(KAGRetriever):
    def __init__(
        self,
        ner_prompt: PromptABC = None,
        std_prompt: PromptABC = None,
        pagerank_threshold: float = 0.9,
        match_threshold: float = 0.9,
        pagerank_weight: float = 0.5,
        reranker_model_path: str = None,
        llm_client: LLMClient = None,
        vectorize_model: VectorizeModelABC = None,
        **kwargs,
    ):
        super().__init__(
            ner_prompt,
            std_prompt,
            pagerank_threshold,
            match_threshold,
            pagerank_weight,
            reranker_model_path,
            llm_client,
            vectorize_model,
        )
        self.text_sim = TextSimilarity(vectorizer=self.vectorize_model)

    def rerank(self, queries: List[str], passages: List[str]):
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
        return new_passages[:10]

    def recall_docs(self, query: str, top_k=5, **kwargs):
        all_related_entities = kwargs.get("related_entities", None)
        query_ner_dict = kwargs.get("query_ner_dict", None)
        req_id = kwargs.get("req_id", "")
        if all_related_entities is None:
            return super().recall_docs(query, top_k, **kwargs)
        return self.recall_docs_by_entities(
            query, all_related_entities, top_k, req_id, query_ner_dict
        )

    def get_std_ner_by_query(self, query: str):
        """
        Retrieves standardized Named Entity Recognition (NER) results based on the input query.

        Parameters:
        query (str): The input query string.

        Returns:
        dict: A dictionary containing standardized entity names and types along with their scores.
        """
        entities = self.named_entity_recognition(query)
        entities_with_official_name = self.named_entity_standardization(query, entities)

        query_ner_list = entities_with_official_name
        try:
            names = []
            for x in query_ner_list:
                x_type = x.get("category", "Others").lower()
                if x_type in ["works", "person", "other"]:
                    names.append(x["entity"])
                else:
                    names.append(x["official_name"])
        except:
            names = [x["entity"] for x in query_ner_list if "entity" in x]
        types = [x["category"] for x in query_ner_list if "category" in x]

        query_ner_list = names
        query_ner_type_list = types

        top_phrases = []
        top_phrase_scores = []

        if len(query_ner_list) > 0:
            (top_phrases, top_phrase_scores) = self.match_entities(
                dict(zip(query_ner_list, query_ner_type_list))
            )
        return_data = {}
        for i in range(0, len(top_phrases)):
            phrases = top_phrases[i]
            phrases["score"] = top_phrase_scores[i]
            return_data[f"{phrases['name']}_{phrases['type']}"] = phrases
        return return_data

    def recall_docs_by_entities(
        self,
        query: str,
        all_related_entities: List[EntityData],
        top_k=10,
        req_id="",
        query_ner_dict: dict = None,
    ):
        def convert_entity_data_to_ppr_cand(related_entities: List[EntityData]):
            ret_ppr_candis = {}
            for e in related_entities:
                k = f"{e.name}_{e.type}"
                ret_ppr_candis[k] = {"name": e.name, "type": e.type, "score": e.score}
            return ret_ppr_candis

        start_time = time.time()
        ner_cands = self.get_std_ner_by_query(query)
        try:
            kg_cands = convert_entity_data_to_ppr_cand(all_related_entities)
        except Exception as e:
            kg_cands = {}
            logger.warning(
                f"{req_id} {query} generate logic form failed {str(e)}", exc_info=True
            )
        for k, v in ner_cands.items():
            if k in kg_cands.keys():
                if v["score"] > kg_cands[k]["score"]:
                    kg_cands[k]["score"] = v["score"]
            else:
                kg_cands[k] = v
        if query_ner_dict is not None:
            for k, v in query_ner_dict.items():
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
        logger.info(f"{req_id} kgpath ner cost={time.time() - start_time}")

        start_time = time.time()
        if len(matched_entities) == 0:
            combined_scores = self.calculate_sim_scores(query, top_k * 20)
            logger.info(f"{req_id} only get_dpr_scores cost={time.time() - start_time}")
        elif (
            matched_entities_scores
            and np.min(matched_entities_scores) > self.pagerank_threshold
        ):  # high confidence in named entities
            combined_scores = self.calculate_pagerank_scores(matched_entities)
        else:
            # Run Personalized PageRank (PPR) or other Graph Algorithm Doc Scores
            pagerank_scores = self.calculate_pagerank_scores(matched_entities)
            logger.info(f"{req_id} only get_ppr_scores cost={time.time() - start_time}")
            start_time = time.time()
            sim_doc_scores = self.calculate_sim_scores(query, top_k * 20)
            logger.info(f"{req_id} only get_dpr_scores cost={time.time() - start_time}")

            combined_scores = self.calculate_combined_scores(
                sim_doc_scores, pagerank_scores
            )

        # Return ranked docs and ranked scores
        sorted_doc_ids = sorted(
            combined_scores.items(), key=lambda item: item[1], reverse=True
        )
        logger.debug(f"kgpath chunk recall cost={time.time() - start_time}")
        return self.get_all_docs_by_id(query, sorted_doc_ids, top_k)
