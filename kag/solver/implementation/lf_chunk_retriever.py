import os
import time
from typing import List

import numpy as np

from kag.common.retriever import DefaultRetriever
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity, cosine_similarity
from kag.solver.logic.core_modules.retriver.retrieval_spo import logger
from knext.project.client import ProjectClient


class LFChunkRetriever(DefaultRetriever):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        vectorizer_config = eval(os.getenv("KAG_VECTORIZER", "{}"))
        if self.host_addr and self.project_id:
            config = ProjectClient(host_addr=self.host_addr, project_id=self.project_id).get_config(self.project_id)
            vectorizer_config.update(config.get("vectorizer", {}))
        self.text_sim = TextSimilarity(vec_config=vectorizer_config)

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
            scores = [cosine_similarity(np.array(query_emb), np.array(passage_emb)) for passage_emb in passages_embs]
            sorted_idx = np.argsort(-np.array(scores))
            for rank, passage_id in enumerate(sorted_idx):
                passage_scores[passage_id] += rank_scores[rank]

        merged_sorted_idx = np.argsort(-passage_scores)

        new_passages = [passages[x] for x in merged_sorted_idx]
        return new_passages[:10]

    def recall_docs(self, query: str, top_k=5, **kwargs):
        all_related_entities = kwargs.get('related_entities', None)
        query_ner_dict = kwargs.get('query_ner_dict', None)
        req_id = kwargs.get('req_id', '')
        if all_related_entities is None:
            return super().recall_docs(query, top_k, **kwargs)
        return self.recall_docs_by_entities(query, all_related_entities, top_k, req_id, query_ner_dict)

    def get_std_ner_by_query(self, query: str):
        """
        Retrieves standardized Named Entity Recognition (NER) results based on the input query.

        Parameters:
        query (str): The input query string.

        Returns:
        dict: A dictionary containing standardized entity names and types along with their scores.
        """
        entities = self.named_entity_recognition(query)
        entities_with_official_name = self.named_entity_standardization(
            query, entities
        )

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

    def recall_docs_by_entities(self, query: str, all_related_entities: List[EntityData], top_k=10,
                                req_id='', query_ner_dict: dict = None):
        def convert_entity_data_to_ppr_cand(related_entities: List[EntityData]):
            ret_ppr_candis = {}
            for e in related_entities:
                k = f"{e.name}_{e.type}"
                ret_ppr_candis[k] = {
                    'name': e.name,
                    'type': e.type,
                    'score': e.score
                }
            return ret_ppr_candis

        start_time = time.time()
        ner_cands = self.get_std_ner_by_query(query)
        try:
            kg_cands = convert_entity_data_to_ppr_cand(all_related_entities)
        except Exception as e:
            kg_cands = {}
            logger.warning(f"{req_id} {query} generate logic form failed {str(e)}", exc_info=True)
        for k, v in ner_cands.items():
            if k in kg_cands.keys():
                if v['score'] > kg_cands[k]['score']:
                    kg_cands[k]['score'] = v['score']
            else:
                kg_cands[k] = v
        if query_ner_dict is not None:
            for k, v in query_ner_dict.items():
                if k in kg_cands.keys():
                    if v['score'] > kg_cands[k]['score']:
                        kg_cands[k]['score'] = v['score']
                else:
                    kg_cands[k] = v

        matched_entities = []
        matched_entities_scores = []
        for _, v in kg_cands.items():
            matched_entities.append(v)
            matched_entities_scores.append(v['score'])
        logger.info(f"{req_id} kgpath ner cost={time.time() - start_time}")

        start_time = time.time()
        if len(matched_entities) == 0:
            combined_scores = self.calculate_sim_scores(query, top_k * 20)
            logger.info(f"{req_id} only get_dpr_scores cost={time.time() - start_time}")
        elif (
                matched_entities_scores and np.min(matched_entities_scores) > self.pagerank_threshold
        ):  # high confidence in named entities
            combined_scores = self.calculate_pagerank_scores(matched_entities)
        else:
            # Run Personalized PageRank (PPR) or other Graph Algorithm Doc Scores
            pagerank_scores = self.calculate_pagerank_scores(matched_entities)
            logger.info(f"{req_id} only get_ppr_scores cost={time.time() - start_time}")
            start_time = time.time()
            sim_doc_scores = self.calculate_sim_scores(query, top_k * 20)
            logger.info(f"{req_id} only get_dpr_scores cost={time.time() - start_time}")

            combined_scores = self.calculate_combined_scores(sim_doc_scores, pagerank_scores)

        # Return ranked docs and ranked scores
        sorted_doc_ids = sorted(
                combined_scores.items(), key=lambda item: item[1], reverse=True
            )
        logger.debug(f"kgpath chunk recall cost={time.time() - start_time}")
        return self.get_all_docs_by_id(query, sorted_doc_ids, top_k)