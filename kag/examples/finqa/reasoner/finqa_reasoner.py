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


class FinQALFExecuteResult(LFExecuteResult):

    def __init__(self):
        super().__init__()

    def get_support_facts(self):
        context_list = []
        for i, lf_plan in enumerate(self.sub_plans):
            if lf_plan.sub_query_type == "math":
                answer = f"The result calculated by the calculator is: {lf_plan.res.sub_answer}"
            else:
                answer = "\n".join(self._norm_doc_retrieved(lf_plan.res.doc_retrieved))
            context_list.append((lf_plan.query, lf_plan.sub_query_type, answer))
        context_str = ""
        for i, c in enumerate(context_list):
            context_str += (
                f"\nSubQuestion{i+1}: {c[0]} by: {c[1]}\nAnswer{i+1}: {c[2]}\n"
            )
        return context_str

    def _norm_doc_retrieved(self, docs):
        rst_list = []
        for doc in docs:
            doc = doc.strip("#")
            x = doc.rfind("#")
            doc = doc[:x]
            rst_list.append(doc)
        return rst_list


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

    def reason1(self, question: str, memory: KagMemoryABC = None, **kwargs):
        step_index = -1
        process_info = {"kg_solved_answer": [], "sub_qa_pair": [], "lf_plan": []}
        history = []
        while True:
            plan_and_result_list = []
            step_index += 1
            if step_index >= 10:
                break
            if 0 == step_index:
                lf_nodes = self.lf_planner._parse_lf(
                    question,
                    [question],
                    ["Retrieval(s=s1:EntityType[`s1`],p=p1:p,o=o1)"],
                )
            else:
                # logic form planing
                lf_nodes: List[LFPlan] = self.lf_planner.lf_planing(
                    question,
                    process_info=process_info,
                    history=history,
                )
            if lf_nodes is None or len(lf_nodes) <= 0:
                break
            for lf_node in lf_nodes:
                rst: LFExecuteResult = self.lf_executor.execute(
                    question,
                    [lf_node],
                    step_index=step_index,
                    process_info=process_info,
                    history=history,
                    **kwargs,
                )
                plan_and_result_list.append((lf_node, rst))

        pass

    def reason(
        self,
        question: str,
        memory: KagMemoryABC = None,
        use_raw_query: bool = True,
        **kwargs,
    ):
        step_index = -1
        process_info = {"kg_solved_answer": [], "sub_qa_pair": [], "goal": question}
        history = []
        while True:
            step_index += 1
            if step_index >= 10:
                break
            if 0 == step_index and use_raw_query:
                lf_nodes = self.lf_planner._parse_lf(
                    question,
                    [question],
                    ["Retrieval(s=s1:EntityType[`s1`],p=p1:p,o=o1)"],
                )
            else:
                # logic form planing
                lf_nodes: List[LFPlan] = self.lf_planner.lf_planing(
                    question,
                    process_info=process_info,
                    history=history,
                )
            if lf_nodes is None or len(lf_nodes) <= 0:
                # TODO reflect
                break
            for lf_node in lf_nodes:
                rst: LFExecuteResult = self.lf_executor.execute(
                    question,
                    [lf_node],
                    step_index=step_index,
                    process_info=process_info,
                    history=history,
                    **kwargs,
                )
                self._use_doc_as_subanswer(history=history, process_info=process_info)

        reason_res: LFExecuteResult = FinQALFExecuteResult()
        all_recall_docs = set()
        for h in history:
            all_recall_docs.update(h.res.doc_retrieved)
        all_recall_docs = list(all_recall_docs)
        reason_res.recall_docs = all_recall_docs
        reason_res.rerank_docs = all_recall_docs
        reason_res.sub_plans = list(history)
        self._print_proceed_info(question, process_info)
        return reason_res

    def _use_doc_as_subanswer(self, history, process_info):
        context_list = []
        process_info["sub_qa_pair"] = []
        for _, lf_plan in enumerate(history):
            if lf_plan.sub_query_type == "math":
                answer = f"The result calculated by the calculator is: {lf_plan.res.sub_answer}"
            else:
                answer = "\n".join(self._norm_doc_retrieved(lf_plan.res.doc_retrieved))
            context_list.append((lf_plan.query, lf_plan.sub_query_type, answer))
        for c in context_list:
            process_info["sub_qa_pair"].append((c[0], c[2]))
        return process_info

    def _norm_doc_retrieved(self, docs):
        rst_list = []
        for doc in docs:
            doc = doc.strip("#")
            x = doc.rfind("#")
            doc = doc[:x]
            rst_list.append(doc)
        return rst_list

    def _print_proceed_info(self, question, process_info):
        logger.info(f"question: {question}")
        for i, qa in enumerate(process_info["sub_qa_pair"]):
            logger.info(f"sub_qa_pair_{i}: {qa[0]}\n{qa[1]}")

    def _reflect(self):
        pass

    def _rerank_docs(
        self, question: str, plan_and_result_list: List, process_info: Dict
    ):
        all_select_list = []
        all_select_list.extend(process_info["lf_plan"])
        all_select_list.extend(plan_and_result_list)
        if (
            len(plan_and_result_list) == 1
            and plan_and_result_list[0][1].if_answered
            and plan_and_result_list[0][0].sub_query_type.lower() == "math"
        ):
            return all_select_list
        for_select_list = []
        for lf_node, res in all_select_list:
            lf_node: LFPlan = lf_node
            if not lf_node.res.if_answered:
                continue
            res: LFExecuteResult = res
            for_select_list.append((lf_node, res))
        if len(for_select_list) == 0:
            return []
        input_chunk_str = ""
        for i, doc in enumerate(for_select_list):
            select_doc_str = f"SubQuestion: {doc[0].query} by: {doc[0].sub_query_type}\nAnswer: {doc[1].sub_answer}\n"
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
            best_chunks.append(for_select_list[index])
        return best_chunks

    def get_context_str(self, process_info: Dict):
        context_list = []
        for i, qa in enumerate(process_info["sub_qa_pair"]):
            a = qa[1]
            lf_plan = process_info["lf_plan"][i][0]
            context_list.append((lf_plan.query, lf_plan.sub_query_type, a))
        context_str = ""
        for i, c in enumerate(context_list):
            context_str += (
                f"\nSubQuestion{i+1}: {c[0]} by: {c[1]}\nAnswer{i+1}: {c[2]}\n"
            )
        if len(context_str) == 0:
            return "No selected chunks"
        return context_str
