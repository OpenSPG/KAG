import os
from typing import List

import numpy as np

from kag.common.vectorizer import Vectorizer


def cosine_similarity(vector1, vector2):
    cosine = np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))
    return cosine

def split_list(input_list, max_length=30):
    """
    Splits a list into multiple sublists where each sublist has a maximum length of max_length.

    :param input_list: The original list to be split
    :param max_length: The maximum length of each sublist
    :return: A list containing multiple sublists
    """
    return [input_list[i:i + max_length] for i in range(0, len(input_list), max_length)]


class TextSimilarity:
    def __init__(self, vec_config=None):
        if vec_config is None:
            vec_config = eval(os.getenv("KAG_VECTORIZER"))
            if vec_config is None:
                message = "vectorizer config is required"
                raise RuntimeError(message)
        self._vectorizer: Vectorizer = Vectorizer.from_config(vec_config)

        self.cached_embs = {}

    def sentence_encode(self, sentences, is_cached=False):
        if isinstance(sentences, str):
            return self._vectorizer.vectorize(sentences)
        if not isinstance(sentences, list):
            return []
        if len(sentences) == 0:
            return []
        ready_list = split_list(sentences)
        ret = []
        for text_list in ready_list:
            tmp_map = {}
            need_call_emb_text = []
            for text in text_list:
                if text in self.cached_embs:
                    tmp_map[text] = self.cached_embs[text]
                else:
                    need_call_emb_text.append(text)
            if len(need_call_emb_text) > 0:
                emb_res = self._vectorizer.vectorize(need_call_emb_text)
                for text, text_emb in zip(need_call_emb_text, emb_res):
                    tmp_map[text] = text_emb
                    if is_cached:
                        self.cached_embs[text] = text_emb
            for text in text_list:
                ret.append(tmp_map[text])
        return ret

    def text_sim_result(self, mention, candidates: List[str], topk=1, low_score=0.63):
        '''
        output: [(candi_name, candi_score),...]
        '''
        if mention is None:
            return []
        mention_emb = self.sentence_encode(mention)
        candidates = [cand for cand in candidates if cand is not None and cand.strip() != '']
        if len(candidates) == 0:
            return []
        candidates_emb = self.sentence_encode(candidates)
        candidates_dis = {}
        for candidate, candidate_emb in zip(candidates, candidates_emb):
            cosine = cosine_similarity(np.array(mention_emb), np.array(candidate_emb))
            if cosine < low_score:
                continue
            candidates_dis[candidate] = cosine
        candidates_dis = sorted(candidates_dis.items(), key=lambda x:x[-1], reverse=True)
        candis = candidates_dis[:topk]
        return candis

    def text_type_sim(self, mention, candidates, topk=1):
        '''
        output: [(candi_name, candi_score),...]
        '''
        res = self.text_sim_result(mention, candidates, topk)
        if len(res) == 0:
            return [('Entity', 1.)]
        return res
