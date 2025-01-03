from typing import List

from kag.common.conf import KAG_CONFIG

from kag.interface import VectorizeModelABC
from kag.interface.solver.execute.lf_sub_query_merger_abc import LFSubQueryResMerger
from kag.interface.solver.base_model import LFExecuteResult, LFPlan
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.retriever.chunk_retriever import ChunkRetriever


@LFSubQueryResMerger.register("default_lf_sub_query_res_merger", as_default=True)
class DefaultLFSubQueryResMerger(LFSubQueryResMerger):
    """
    Initializes the base planner.
    """

    def __init__(
        self,
        chunk_retriever: ChunkRetriever,
        vectorize_model: VectorizeModelABC = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.chunk_retriever = chunk_retriever
        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            KAG_CONFIG.all_config["vectorize_model"]
        )
        self.text_similarity = TextSimilarity(vectorize_model)

    def merge(self, query, lf_res_list: List[LFPlan]) -> LFExecuteResult:
        res = LFExecuteResult()
        res.sub_plans = lf_res_list
        rerank_docs, recall_docs = self._rerank_called_all_docs(query, lf_res_list)
        res.rerank_docs = rerank_docs
        res.recall_docs = recall_docs
        return res

    def _rerank_called_all_docs(self, query, lf_res_list: List[LFPlan]):
        passages_set = [lf_res.res.doc_retrieved for lf_res in lf_res_list]
        recall_docs = self._flat_passages_set(passages_set)
        sub_queries = [lf_res.query for lf_res in lf_res_list]
        rerank_docs = self.chunk_retriever.rerank_docs(
            [query] + sub_queries, recall_docs
        )
        return rerank_docs, recall_docs

    def _flat_passages_set(self, passages_set: list):
        """
        Flattens the passages set and scores each passage based on its position.

        Parameters:
        passages_set (list): A list of passage sets.

        Returns:
        list: A list of passages sorted by their scores.
        """
        score_map = {}
        for passages in passages_set:
            passages = ["#".join(item.split("#")[:-1]) for item in passages]
            for i, passage in enumerate(passages):
                score = 1.0 / (1 + i)
                if passage in score_map:
                    score_map[passage] += score
                else:
                    score_map[passage] = score

        return [
            k
            for k, v in sorted(
                score_map.items(), key=lambda item: item[1], reverse=True
            )
        ]
