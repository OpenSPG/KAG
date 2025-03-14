import logging
import os
import copy
from typing import List, Dict, Tuple
from multiprocessing import Pool

import chromadb

from kag.interface.solver.execute.lf_executor_abc import LFExecutorABC
from kag.interface.solver.kag_reasoner_abc import KagReasonerABC
from kag.interface.solver.kag_memory_abc import KagMemoryABC
from kag.interface.solver.plan.lf_planner_abc import LFPlannerABC
from kag.interface.solver.base_model import LFExecuteResult, LFPlan
from kag.interface import LLMClient
from kag.interface.solver.base_model import LFExecuteResult
from kag.solver.utils import init_prompt_with_fallback
from kag.solver.tools.search_api.search_api_abc import SearchApiABC
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from knext.schema.client import CHUNK_TYPE, OTHER_TYPE
from kag.interface import VectorizeModelABC as Vectorizer
from kag.common.conf import KAG_CONFIG
from kag.common.conf import KAG_PROJECT_CONF

logger = logging.getLogger()

from kag.examples.finqa.reasoner.common import (
    get_history_context_info_list,
    get_history_context_str,
    get_all_recall_docs,
    get_execute_context,
)


class FinQALFExecuteResult(LFExecuteResult):

    def __init__(self, question, execute_rst_list: list[LFExecuteResult]):
        super().__init__()
        self.question = question
        self.execute_rst_list = execute_rst_list

    def get_support_facts(self):
        context_list = get_execute_context(self.question, self.execute_rst_list)
        context_str = get_history_context_str(context_list=context_list)
        return context_str

    def get_trace_log(self):
        context_list = get_execute_context(self.question, self.execute_rst_list)
        context_str = get_history_context_str(context_list=context_list)
        code = ""
        try:
            code = context_list[-1][3]["code"]
        except:
            pass
        return {
            "sub question": context_str,
            "recall docs": self.recall_docs,
            "rerank docs": self.rerank_docs,
            "kg_exact_solved_answer": self.kg_exact_solved_answer,
            "code": code,
        }


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

        self.question_classify_prompt = init_prompt_with_fallback(
            "question_classify", self.biz_scene
        )
        current_dir = os.path.dirname(os.path.abspath(__file__))
        chromadb_path = os.path.join(current_dir, "..", "dyna_shot", "chromadb")
        self.chroma_client = chromadb.PersistentClient(path=chromadb_path)
        self.collection = self.chroma_client.create_collection(
            name="finqa_example", get_or_create=True
        )

    def question_classify(self, question):
        llm: LLMClient = self.llm_module
        params = {"question": question}
        tags = llm.invoke(
            variables=params,
            prompt_op=self.question_classify_prompt,
            with_json_parse=False,
            with_except=True,
        )
        return tags

    def retrieval_examples(self, question, tags, topn=3):
        doc = question + " tags=" + str(tags)
        rsts = self.collection.query(query_texts=[doc], n_results=topn)
        examples = []
        for meta in rsts["metadatas"][0]:
            examples.append(meta["example"])
        return examples

    def reason(
        self,
        question: str,
        memory: KagMemoryABC = None,
        use_raw_query: bool = False,
        **kwargs,
    ):
        tags = self.question_classify(question=question)
        examples = self.retrieval_examples(question=question, tags=tags)
        step_index = -1
        execute_rst_list = []
        process_info = {
            "kg_solved_answer": [],
            "sub_qa_pair": [],
            "goal": question,
            "examples": examples,
            "execute_rst_list": execute_rst_list,
        }
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
                    execute_rst_list=execute_rst_list,
                )
            self._remove_duplicate_lf(
                execute_rst_list=execute_rst_list, lf_nodes=lf_nodes
            )
            if lf_nodes is None or len(lf_nodes) <= 0:
                # TODO reflect
                break
            rst: LFExecuteResult = self.lf_executor.execute(
                question,
                lf_nodes,
                step_index=step_index,
                process_info=process_info,
                **kwargs,
            )
            execute_rst_list.append(rst)

            self._use_doc_as_subanswer(
                question=question,
                execute_rst_list=execute_rst_list,
                process_info=process_info,
            )
            # 如果所有node都没有结果
            if not get_all_recall_docs(execute_rst_list=execute_rst_list):
                break

        reason_res: LFExecuteResult = FinQALFExecuteResult(
            question=question, execute_rst_list=execute_rst_list
        )

        return reason_res

    def _remove_duplicate_lf(self, execute_rst_list, lf_nodes):
        query_set = set()
        for exe_info in execute_rst_list:
            exe_info: LFExecuteResult = exe_info
            for lf in exe_info.sub_plans:
                lf: LFPlan = lf
                query_set.add(lf.query)
        return [lf for lf in lf_nodes if lf.query not in query_set]

    def _use_doc_as_subanswer(self, question, execute_rst_list, process_info):
        context_list = get_execute_context(
            question=question, execute_rst_list=execute_rst_list
        )
        process_info["sub_qa_pair"] = []
        for c in context_list:
            process_info["sub_qa_pair"].append((c[0], c[2]))
        return process_info
