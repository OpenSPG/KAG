import logging
from typing import List, Dict

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import LLMClient
from kag.interface.solver.execute.lf_executor_abc import LFExecutorABC
from kag.interface.solver.execute.lf_sub_query_merger_abc import LFSubQueryResMerger
from kag.solver.execute.op_executor.op_deduce.deduce_executor import DeduceExecutor
from kag.solver.execute.op_executor.op_math.math_executor import MathExecutor
from kag.solver.execute.op_executor.op_output.output_executor import OutputExecutor
from kag.solver.execute.op_executor.op_retrieval.retrieval_executor import (
    RetrievalExecutor,
)
from kag.interface.solver.base_model import LFExecuteResult, LFPlan, SubQueryResult
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.utils import generate_random_string
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.retriever.chunk_retriever import ChunkRetriever
from kag.solver.retriever.exact_kg_retriever import ExactKgRetriever
from kag.solver.retriever.fuzzy_kg_retriever import FuzzyKgRetriever
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool

logger = logging.getLogger()


@LFExecutorABC.register("default_lf_executor", as_default=True)
class DefaultLFExecutor(LFExecutorABC):
    def __init__(
        self,
        merger: LFSubQueryResMerger,
        exact_kg_retriever: ExactKgRetriever = None,
        fuzzy_kg_retriever: FuzzyKgRetriever = None,
        chunk_retriever: ChunkRetriever = None,
        force_chunk_retriever: bool = False,
        llm_client: LLMClient = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.params = kwargs

        # tmp graph data
        self.schema: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
                }
            )
        )

        self.exact_kg_retriever = exact_kg_retriever
        self.fuzzy_kg_retriever = fuzzy_kg_retriever
        self.chunk_retriever = chunk_retriever
        self.force_chunk_retriever = force_chunk_retriever
        self.params["exact_kg_retriever"] = exact_kg_retriever
        self.params["fuzzy_kg_retriever"] = fuzzy_kg_retriever
        self.params["chunk_retriever"] = chunk_retriever
        self.params["force_chunk_retriever"] = force_chunk_retriever
        self.params["llm_module"] = llm_client

        self.merger: LFSubQueryResMerger = merger

        # Initialize executors for different operations.
        self.retrieval_executor = RetrievalExecutor(schema=self.schema, **self.params)
        self.deduce_executor = DeduceExecutor(schema=self.schema, **self.params)
        self.math_executor = MathExecutor(schema=self.schema, **self.params)
        self.output_executor = OutputExecutor(schema=self.schema, **self.params)

    def _execute_spo_answer(
        self,
        req_id: str,
        query: str,
        lf: LFPlan,
        process_info: Dict,
        kg_graph: KgGraph,
        history: List[LFPlan]
    ) -> SubQueryResult:
        # Execute graph retrieval operations.
        if self.retrieval_executor.is_this_op(lf.lf_node):
            self.retrieval_executor.executor(query, lf, req_id, kg_graph, process_info, history, self.params)
        elif self.deduce_executor.is_this_op(lf.lf_node):
            self.deduce_executor.executor(query, lf, req_id, kg_graph, process_info, history, self.params)
        elif self.math_executor.is_this_op(lf.lf_node):
            self.math_executor.executor(query, lf, req_id, kg_graph, process_info, history, self.params)
        elif self.output_executor.is_this_op(lf.lf_node):
            self.output_executor.executor(query, lf, req_id, kg_graph, process_info, history, self.params)
        else:
            logger.warning(f"unknown operator: {lf.lf_node.operator}")
        lf.res.is_executed = True
        return lf.res

    def _execute_lf(
        self,
        req_id: str,
        query: str,
        index: int,
        lf: LFPlan,
        process_info: Dict,
        kg_graph: KgGraph,
        history: List[LFPlan],
        **kwargs,
    ) -> (SubQueryResult, bool):
        # change node state from WAITING to RUNNING
        is_break = False
        self._update_sub_question_status(
            report_tool=kwargs.get("report_tool", None),
            req_id=req_id,
            index=index,
            status=ReporterIntermediateProcessTool.STATE.RUNNING,
            plan=lf,
            kg_graph=kg_graph,
        )
        res = self._execute_spo_answer(
            req_id, query, lf, process_info, kg_graph, history
        )
        # update node state information
        self._update_sub_question_status(
            report_tool=kwargs.get("report_tool", None),
            req_id=req_id,
            index=index,
            status=ReporterIntermediateProcessTool.STATE.RUNNING,
            plan=lf,
            kg_graph=kg_graph,
        )

        if not res.if_answered:
            is_break = True

        # change node state from RUNNING to FINISH
        self._update_sub_question_status(
            report_tool=kwargs.get("report_tool", None),
            req_id=req_id,
            index=index,
            status=ReporterIntermediateProcessTool.STATE.FINISH,
            plan=lf,
            kg_graph=kg_graph,
        )
        return res, is_break

    def execute_kg_retrieval_first(self, req_id, query, lf_nodes: List[LFPlan],process_info, kg_graph, history) -> List[LFPlan]:
        # execute kg retriever first
        lf_set = []
        for lf in lf_nodes:
            if lf.sub_query_type == "retrieval":
                self._execute_spo_answer(
                    req_id, query, lf, process_info, kg_graph, history
                )
        return lf_set


    def execute(self, query, lf_nodes: List[LFPlan], **kwargs) -> LFExecuteResult:
        self._create_report_pipeline(kwargs.get("report_tool", None), query, lf_nodes)
        process_info = {
            "kg_solved_answer": [],
            "sub_qa_pair": []
        }
        kg_graph = KgGraph()
        history = []
        # Process each sub-query.
        for idx, lf in enumerate(lf_nodes):
            res = SubQueryResult()
            res.sub_query = lf.query
            lf.res = res
            process_info[lf.query] = {
                "spo_retrieved": [],
                "doc_retrieved": [],
                "if_answered": False,
                "match_type": "chunk",
                "kg_answer": "",
            }
        self.execute_kg_retrieval_first(
                req_id=generate_random_string(10),
                query=query,
                lf_nodes=lf_nodes,
                process_info=process_info,
                kg_graph=kg_graph,
                history=history)
        for idx, lf in enumerate(lf_nodes):
            sub_result, is_break = self._execute_lf(
                req_id=generate_random_string(10),
                index=idx + 1,
                query=query,
                lf=lf,
                process_info=process_info,
                kg_graph=kg_graph,
                history=history,
                **kwargs,
            )
            lf.res = sub_result
            process_info['sub_qa_pair'].append([
                lf.query,
                sub_result.sub_answer
            ])
            history.append(lf)
            if is_break:
                break
        # merge all results
        res = self.merger.merge(query, history)
        res.retrieved_kg_graph = kg_graph
        res.kg_exact_solved_answer = "\n".join(process_info["kg_solved_answer"])
        return res

    def _create_report_pipeline(
        self, report_tool: ReporterIntermediateProcessTool, query, lf_nodes
    ):
        if report_tool:
            report_tool.report_pipeline(query, lf_nodes)

    def _update_sub_question_status(
        self,
        report_tool: ReporterIntermediateProcessTool,
        req_id,
        index,
        status,
        plan: LFPlan,
        kg_graph: KgGraph,
    ):
        if report_tool:
            report_tool.report_node(req_id, index, status, plan, kg_graph)
