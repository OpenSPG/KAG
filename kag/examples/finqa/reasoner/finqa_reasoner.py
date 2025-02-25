import logging
import copy
from typing import List, Dict

from kag.interface.solver.execute.lf_executor_abc import LFExecutorABC
from kag.interface.solver.kag_reasoner_abc import KagReasonerABC
from kag.interface.solver.kag_memory_abc import KagMemoryABC
from kag.interface.solver.plan.lf_planner_abc import LFPlannerABC
from kag.interface.solver.base_model import LFExecuteResult, LFPlan
from kag.interface import LLMClient
from kag.interface.solver.base_model import LFExecuteResult
from kag.solver.utils import init_prompt_with_fallback

logger = logging.getLogger()


@KagReasonerABC.register("finqa_reasoner", as_default=True)
class FinQAReasoner(KagReasonerABC):
    """
    A processor class for handling logical form tasks in language processing.

    This class uses an LLM module (llm_module) to plan, retrieve, and solve logical forms.

    Parameters:
    - lf_planner (LFBasePlanner): The planner for structuring logical forms. Defaults to None. If not provided, the default implementation of LFPlanner is used.
    - lf_executor: Instance of the logical form executor, which solves logical form problems. If not provided, the default implementation of LFSolver is used.

    Attributes:
    - lf_planner: Instance of the logical form planner.
    - lf_solver: Instance of the logical form solver, which solves logical form problems.
    - sub_query_total: Total number of sub-queries processed.
    - kg_direct: Number of direct knowledge graph queries.
    - trace_log: List to log trace information.
    """

    def __init__(
        self,
        lf_planner: LFPlannerABC,
        lf_executor: LFExecutorABC,
        llm_client: LLMClient = None,
        **kwargs,
    ):
        super().__init__(llm_client, **kwargs)

        self.lf_planner = lf_planner

        self.lf_executor = lf_executor
        self.sub_query_total = 0
        self.kg_direct = 0
        self.trace_log = []

        self.rerank_docs_prompt = init_prompt_with_fallback(
            "rerank_chunks", self.biz_scene
        )

    def reason(self, question: str, memory: KagMemoryABC = None, **kwargs):
        """
        Processes a given question by planning and executing logical forms to derive an answer.

        Parameters:
        - question (str): The input question to be processed.

        Returns:
        - solved_answer: The final answer derived from solving the logical forms.
        - supporting_fact: Supporting facts gathered during the reasoning process.
        - history_log: A dictionary containing the history of QA pairs and re-ranked documents.
        """
        plan_and_result_list = []
        step_index = -1
        process_info = {"kg_solved_answer": [], "sub_qa_pair": []}
        while True:
            step_index += 1
            # logic form planing
            lf_nodes: List[LFPlan] = self.lf_planner.lf_planing(
                question, process_info=process_info
            )
            if lf_nodes is None or len(lf_nodes) <= 0:
                break
            for lf_node in lf_nodes:
                rst: LFExecuteResult = self.lf_executor.execute(
                    question,
                    [lf_node],
                    step_index=step_index,
                    process_info=process_info,
                    **kwargs,
                )
                plan_and_result_list.append((lf_node, rst))

            # rerank docs
            best_chunk, lf_node = self._rerank_docs(
                question, plan_and_result_list, process_info
            )
            lf_node: LFPlan = lf_node
            process_info["sub_qa_pair"].append((lf_node, best_chunk))

        reason_res: LFExecuteResult = LFExecuteResult()
        reason_res.recall_docs = [p[1] for p in process_info["sub_qa_pair"]]
        reason_res.rerank_docs = [p[1] for p in process_info["sub_qa_pair"]]
        reason_res.sub_plans = [p[0] for p in process_info["sub_qa_pair"]]
        return reason_res

    def _rerank_docs(
        self, question: str, plan_and_result_list: List, process_info: Dict
    ):
        docs_map = {}
        selected_docs = [p[1] for p in process_info["sub_qa_pair"]]
        for lf_node, res in plan_and_result_list:
            lf_node: LFPlan = lf_node
            res: LFExecuteResult = res
            if "retrieval" == lf_node.sub_query_type:
                for doc_str in res.doc_retrieved:
                    doc_str: str = doc_str.strip()
                    content_start = doc_str.find("#", 1)
                    content_end = doc_str.rfind("#")
                    cuted_doc_str = doc_str[content_start + 1 : content_end]
                    if cuted_doc_str in selected_docs:
                        continue
                    score = float(doc_str[content_end + 1 :])
                    docs_map[cuted_doc_str] = (lf_node, score)
            elif "math" == lf_node.sub_query_type:
                doc_str = f"{res.sub_query}\nCalculated through a program return:\n{res.sub_answer}"
                docs_map[doc_str] = (lf_node, 0.0)
        input_chunk_str = ""
        chunks_str_list = sorted(
            docs_map.keys(), key=lambda x: docs_map[x][1], reverse=True
        )
        index = 0
        for chunk_str in chunks_str_list:
            input_chunk_str += f"\n### {index}\n{chunk_str}\n"
            index += 1
        input_dict = {"question": question, "chunks": input_chunk_str, "context": ""}
        best_chunk_index = self.llm_module.invoke(
            input_dict, self.rerank_docs_prompt, False, True
        )
        best_chunk = chunks_str_list[best_chunk_index]
        return best_chunk, docs_map[best_chunk][0]
