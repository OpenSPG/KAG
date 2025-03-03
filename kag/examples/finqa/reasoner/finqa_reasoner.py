import logging
import copy
from typing import List, Dict, Tuple
from multiprocessing import Pool

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
        step_index = -1
        process_info = {"kg_solved_answer": [], "sub_qa_pair": [], "lf_plan": []}
        while True:
            plan_and_result_list = []
            step_index += 1
            if step_index >= 10:
                break
            # logic form planing
            lf_nodes: List[LFPlan] = self.lf_planner.lf_planing(
                question, process_info=process_info
            )
            lf_nodes = self._filter_lf_nodes(process_info, lf_nodes)
            if lf_nodes is None or len(lf_nodes) <= 0:
                logger.error(f"lf_nodes is None or len(lf_nodes) <= 0")
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
            best_chunks = self._rerank_docs(
                question, plan_and_result_list, process_info
            )
            if best_chunks is None:
                break
            for best_chunk in best_chunks:
                lf_node: LFPlan = best_chunk[0]
                process_info["sub_qa_pair"].append((lf_node.query, best_chunk[1]))
                process_info["lf_plan"].append(lf_node)

        reason_res: LFExecuteResult = LFExecuteResult()
        reason_res.recall_docs = [p[1] for p in process_info["sub_qa_pair"]]
        reason_res.rerank_docs = [p[1] for p in process_info["sub_qa_pair"]]
        reason_res.sub_plans = [p for p in process_info["lf_plan"]]
        self._print_proceed_info(question, process_info)
        return reason_res

    def _print_proceed_info(self, question, process_info):
        logger.info(f"question: {question}")
        for i, qa in enumerate(process_info["sub_qa_pair"]):
            logger.info(f"sub_qa_pair_{i}: {qa[0]}\n{qa[1]}")

    def _filter_lf_nodes(self, process_info, lf_nodes: List[LFPlan]):
        if lf_nodes is None or len(lf_nodes) <= 0:
            return None
        sub_q_set = set()
        for qa in process_info["sub_qa_pair"]:
            sub_q_set.add(qa[0])
        new_lf_nodes = []
        for lf in lf_nodes:
            if lf.query not in sub_q_set:
                new_lf_nodes.append(lf)
        return new_lf_nodes

    def _rerank_docs(
        self, question: str, plan_and_result_list: List, process_info: Dict
    ):
        chunk_set = set()
        for_select_qa_list = []
        selected_docs = [p[1] for p in process_info["sub_qa_pair"]]
        for lf_node, res in plan_and_result_list:
            lf_node: LFPlan = lf_node
            res: LFExecuteResult = res
            if not lf_node.res.if_answered:
                continue
            doc_str = res.sub_answer
            if doc_str in chunk_set or doc_str in selected_docs:
                continue
            chunk_set.add(doc_str)
            for_select_qa_list.append((lf_node, doc_str))
        if len(for_select_qa_list) == 0:
            return None
        input_chunk_str = ""
        for i, doc in enumerate(for_select_qa_list):
            select_doc_str = f"SubQuestion: {doc[0].query} by: {doc[0].sub_query_type}\nAnswer: {doc[1]}\n"
            input_chunk_str += f"\n### {i}\n{select_doc_str}\n"
        input_dict = {
            "question": question,
            "chunks": input_chunk_str,
            "context": self.get_context_str(process_info),
        }
        best_chunk_index_list = self.llm_module.invoke(
            input_dict, self.rerank_docs_prompt, False, True
        )
        if best_chunk_index_list is None:
            logger.error(f"best_chunk_index is None")
            return None
        best_chunks = []
        for index in best_chunk_index_list:
            best_chunks.append(for_select_qa_list[index])
            exists = self.check_best_chunk_exists(
                for_select_qa_list[index][0], process_info
            )
            if exists:
                logger.error(
                    f"best_chunk: {for_select_qa_list[index][0].query} exists in process_info"
                )
                continue
        return best_chunks

    def get_context_str(self, process_info: Dict):
        context_list = []
        for i, qa in enumerate(process_info["sub_qa_pair"]):
            a = qa[1]
            lf_plan = process_info["lf_plan"][i]
            context_list.append((lf_plan.query, lf_plan.sub_query_type, a))
        context_str = ""
        for i, c in enumerate(context_list):
            context_str += (
                f"\nSubQuestion{i+1}: {c[0]} by: {c[1]}\nAnswer{i+1}: {c[2]}\n"
            )
        if len(context_str) == 0:
            return "No selected chunks"
        return context_str

    def check_best_chunk_exists(self, best_chunk_lf_plan: LFPlan, process_info: Dict):
        for p in process_info["lf_plan"]:
            if p.query == best_chunk_lf_plan.query:
                return True
        return False
