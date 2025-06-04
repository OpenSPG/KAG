import numpy as np
from typing import List

from kag.common.conf import KAG_CONFIG
from kag.interface import ToolABC, VectorizeModelABC, RerankModelABC
from kag.interface.solver.model.one_hop_graph import ChunkData
from kag.common.text_sim_by_vector import TextSimilarity, cosine_similarity


def _flat_passages_set(passages_set: List[List[ChunkData]]):
    """
    Flattens the passages set and scores each passage based on its position.

    Parameters:
    passages_set (list): A list of passage sets.

    Returns:
    list: A list of passages sorted by their scores.
    """
    chunk_id_maps = {}
    score_map = {}
    for passages in passages_set:
        for i, passage in enumerate(passages):
            chunk_id_maps[passage.chunk_id] = passage
            score = 1.0 / (1 + i)
            if passage in score_map:
                score_map[passage.chunk_id] += score
            else:
                score_map[passage.chunk_id] = score

    chunk_ids = [
        k for k, v in sorted(score_map.items(), key=lambda item: item[1], reverse=True)
    ]
    result = []
    for i in chunk_ids:
        result.append(chunk_id_maps[i])
    return result


@ToolABC.register("rerank_by_vector")
class RerankByVector(ToolABC):
    def __init__(
        self, vectorize_model: VectorizeModelABC = None, rerank_top_k: int = 10
    ):
        super().__init__()
        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            KAG_CONFIG.all_config["vectorize_model"]
        )
        self.text_sim = TextSimilarity(vectorize_model)
        self.rerank_top_k = rerank_top_k

    def invoke(
        self,
        query,
        sub_queries: List[str],
        sub_question_chunks: List[List[ChunkData]],
        **kwargs,
    ):
        return self.rerank_docs([query] + sub_queries, sub_question_chunks)

    def rerank_docs(self, queries: List[str], chunks: List[List[ChunkData]]):
        if not isinstance(queries, list):
            queries = [queries]
        if len(chunks) == 0:
            return []
        if len(queries) == 1 and len(chunks) == 1:
            return chunks[0]
        flat_chunks = _flat_passages_set(chunks)
        queries = list(set(queries))
        rank_scores = np.array([1 / (1 + i) for i in range(len(flat_chunks))])
        passage_scores = np.zeros(len(flat_chunks)) + rank_scores
        passages = [chunk.content for chunk in flat_chunks]
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

        new_passages = [flat_chunks[x] for x in merged_sorted_idx]
        if self.rerank_top_k > 0:
            return new_passages[: self.rerank_top_k]
        return new_passages


@ToolABC.register("rerank_by_model")
class RerankByModel(ToolABC):
    def __init__(self, rerank_model: RerankModelABC, rerank_top_k: int = 10):
        super().__init__()
        self.rerank_model = rerank_model
        self.rerank_top_k = rerank_top_k

    def invoke(
        self,
        query,
        sub_queries: List[str],
        sub_question_chunks: List[List[ChunkData]],
        **kwargs,
    ):
        return self.rerank_docs([query] + sub_queries, sub_question_chunks)

    def rerank_docs(self, queries: List[str], chunks: List[List[ChunkData]]):
        if not isinstance(queries, list):
            queries = [queries]
        if len(chunks) == 0:
            return []

        queries = list(set(queries))
        flat_chunks = _flat_passages_set(chunks)
        passages = [chunk.content for chunk in flat_chunks]

        new_passages = self.rerank_model.rerank(queries, passages)
        return new_passages[: self.rerank_top_k]
