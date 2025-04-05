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
from kag.solver.execute.op_executor.op_sort.sort_executor import SortExecutor
from kag.solver.execute.sub_query_generator import LFSubGenerator
from kag.interface.solver.base_model import LFExecuteResult, LFPlan, SubQueryResult
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.utils import generate_random_string
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.retriever.chunk_retriever import ChunkRetriever
from kag.solver.retriever.atomic_question_retriever import AtomicQuestionRetriever
from kag.solver.retriever.exact_kg_retriever import ExactKgRetriever
from kag.solver.retriever.fuzzy_kg_retriever import FuzzyKgRetriever
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool
from kag.interface import PromptABC
from kag.solver.utils import init_prompt_with_fallback

logger = logging.getLogger()


@LFExecutorABC.register("lf_with_atomic_question_executor")
class LFWithAtomicQuestionExecutor(LFExecutorABC):
    def __init__(
        self,
        exact_kg_retriever: ExactKgRetriever,
        fuzzy_kg_retriever: FuzzyKgRetriever,
        chunk_retriever: ChunkRetriever,
        atomic_question_retriever: AtomicQuestionRetriever,
        merger: LFSubQueryResMerger,
        force_chunk_retriever: bool = False,
        llm_client: LLMClient = None,
        decomposition_prompt: PromptABC = None,
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
        self.atomic_question_retriever = atomic_question_retriever
        self.force_chunk_retriever = force_chunk_retriever
        self.params["exact_kg_retriever"] = exact_kg_retriever
        self.params["fuzzy_kg_retriever"] = fuzzy_kg_retriever
        self.params["chunk_retriever"] = chunk_retriever
        self.params["atomic_question_retriever"] = atomic_question_retriever
        self.params["force_chunk_retriever"] = force_chunk_retriever
        self.params["llm_module"] = llm_client

        self.decomposition_prompt = decomposition_prompt
        biz_scene = KAG_PROJECT_CONF.biz_scene
        if self.decomposition_prompt is None:
            self.decomposition_prompt = init_prompt_with_fallback("decomposition_query", biz_scene)
        # Generate
        self.generator = LFSubGenerator(llm_client=llm_client)
        self.llm_client = llm_client

        self.merger: LFSubQueryResMerger = merger

        # Initialize executors for different operations.
        self.retrieval_executor = RetrievalExecutor(schema=self.schema, **self.params)
        self.deduce_executor = DeduceExecutor(schema=self.schema, **self.params)
        self.sort_executor = SortExecutor(schema=self.schema, **self.params)
        self.math_executor = MathExecutor(schema=self.schema, **self.params)
        self.output_executor = OutputExecutor(schema=self.schema, **self.params)

    def _judge_sub_answered(self, sub_answer: str):
        return sub_answer and "i don't know" not in sub_answer.lower()

    def _execute_spo_answer(
        self,
        req_id: str,
        query: str,
        lf: LFPlan,
        process_info: Dict,
        kg_graph: KgGraph,
        history: List[LFPlan],
    ) -> SubQueryResult:
        res = SubQueryResult()
        res.sub_query = lf.query
        process_info[lf.query] = {
            "spo_retrieved": [],
            "doc_retrieved": [],
            "match_type": "spo",
            "kg_answer": "",
        }
        # Execute graph retrieval operations.
        for n in lf.lf_nodes:
            if self.retrieval_executor.is_this_op(n):
                self.retrieval_executor.executor(
                    query, n, req_id, kg_graph, process_info, self.params
                )
            elif self.deduce_executor.is_this_op(n):
                self.deduce_executor.executor(
                    query, n, req_id, kg_graph, process_info, self.params
                )
            elif self.math_executor.is_this_op(n):
                self.math_executor.executor(
                    query, n, req_id, kg_graph, process_info, self.params
                )
            elif self.sort_executor.is_this_op(n):
                self.sort_executor.executor(
                    query, n, req_id, kg_graph, process_info, self.params
                )
            elif self.output_executor.is_this_op(n):
                self.output_executor.executor(
                    query, n, req_id, kg_graph, process_info, self.params
                )
            else:
                logger.warning(f"unknown operator: {n.operator}")


        res.spo_retrieved = process_info[lf.query].get("spo_retrieved", [])
        res.sub_answer = process_info[lf.query]["kg_answer"]
        res.doc_retrieved = []
        res.match_type = process_info[lf.query]["match_type"]
        # generate sub answer
        if not self._judge_sub_answered(res.sub_answer) and (
            len(res.spo_retrieved) and not self.force_chunk_retriever
        ):
            # try to use spo to generate answer
            res.sub_answer = self.generator.generate_sub_answer(
                lf.query, res.spo_retrieved, [], history
            )
        return res

    def _execute_atomic_question_answer_with_embedding(
        self,
        req_id: str,
        query: str,
        lf: LFPlan,
        process_info: Dict,
        kg_graph: KgGraph,
        history: List[LFPlan],
        res: SubQueryResult,
    ) -> SubQueryResult:
        if not self._judge_sub_answered(res.sub_answer) or self.force_chunk_retriever:
            if self.force_chunk_retriever:
                # force chunk retriever, so we clear kg solved answer
                process_info["kg_solved_answer"] = []

            sub_query = self._generate_sub_query_with_history_qa(history, lf.query)
            doc_retrieved = self.atomic_question_retriever.recall_chunk_with_atomic_question(
                queries=[query, sub_query],
                kwargs=self.params,
            )
            res.doc_retrieved = doc_retrieved
            process_info[lf.query]["doc_retrieved"] = doc_retrieved
            process_info[lf.query]["match_type"] = "atomic_question"
            # generate sub answer by chunk ans spo
            docs = ["#".join(item.split("#")[:-1]) for item in doc_retrieved]
            res.sub_answer = self.generator.generate_sub_answer(
                lf.query, res.spo_retrieved, docs, history
            )
        return res

    def _execute_atomic_question_answer_with_ppr(
        self,
        req_id: str,
        query: str,
        lf: LFPlan,
        process_info: Dict,
        kg_graph: KgGraph,
        history: List[LFPlan],
        res: SubQueryResult,
    ) -> SubQueryResult:
        if not self._judge_sub_answered(res.sub_answer) or self.force_chunk_retriever:
            if self.force_chunk_retriever:
                # force chunk retriever, so we clear kg solved answer
                process_info["kg_solved_answer"] = []
            # atomic_question to chunk retriever

            all_related_entities = kg_graph.get_all_spo()
            all_related_entities = list(set(all_related_entities))
            sub_query = self._generate_sub_query_with_history_qa(history, lf.query)
            # import pdb;pdb.set_trace()
            doc_retrieved = self.atomic_question_retriever.recall_docs_with_ppr(
                queries=[query, sub_query],
                retrieved_spo=all_related_entities,
                kwargs=self.params,
            )
            res.doc_retrieved = doc_retrieved
            process_info[lf.query]["doc_retrieved"] = doc_retrieved
            process_info[lf.query]["match_type"] = "atomic_question"
            # generate sub answer by chunk ans spo
            docs = ["#".join(item.split("#")[:-1]) for item in doc_retrieved]
            res.sub_answer = self.generator.generate_sub_answer(
                lf.query, res.spo_retrieved, docs, history
            )
        return res

    def _execute_chunk_answer(
        self,
        req_id: str,
        query: str,
        lf: LFPlan,
        process_info: Dict,
        kg_graph: KgGraph,
        history: List[LFPlan],
        res: SubQueryResult,
    ) -> SubQueryResult:
        if not self._judge_sub_answered(res.sub_answer) or self.force_chunk_retriever:
            if self.force_chunk_retriever:
                # force chunk retriever, so we clear kg solved answer
                process_info["kg_solved_answer"] = []
            # chunk retriever
            all_related_entities = kg_graph.get_all_spo()
            all_related_entities = list(set(all_related_entities))
            sub_query = self._generate_sub_query_with_history_qa(history, lf.query)
            doc_retrieved = self.chunk_retriever.recall_docs(
                queries=[query, sub_query],
                retrieved_spo=all_related_entities,
                kwargs=self.params,
            )
            res.doc_retrieved = doc_retrieved
            process_info[lf.query]["doc_retrieved"] = doc_retrieved
            process_info[lf.query]["match_type"] = "chunk"
            # generate sub answer by chunk ans spo
            docs = ["#".join(item.split("#")[:-1]) for item in doc_retrieved]
            ###
            res.sub_answer = self.generator.generate_sub_answer(
                lf.query, res.spo_retrieved, docs, history
            )
        return res

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
    ) -> SubQueryResult:
        # change node state from WAITING to RUNNING
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
        lf.res = res
        # update node state information
        self._update_sub_question_status(
            report_tool=kwargs.get("report_tool", None),
            req_id=req_id,
            index=index,
            status=ReporterIntermediateProcessTool.STATE.RUNNING,
            plan=lf,
            kg_graph=kg_graph,
        )
        if not self._judge_sub_answered(res.sub_answer) or self.force_chunk_retriever:
            # if not found answer in kg, we retrieved atomic_question then transfer to chunk to answer.
            res = self._execute_chunk_answer(
                req_id, query, lf, process_info, kg_graph, history, res
            )
            # res = self._execute_atomic_question_answer_with_embedding(
            #     req_id, query, lf, process_info, kg_graph, history, res
            # )
            # res = self._execute_atomic_question_answer_with_ppr(
            #     req_id, query, lf, process_info, kg_graph, history, res
            # )
        # change node state from RUNNING to FINISH
        self._update_sub_question_status(
            report_tool=kwargs.get("report_tool", None),
            req_id=req_id,
            index=index,
            status=ReporterIntermediateProcessTool.STATE.FINISH,
            plan=lf,
            kg_graph=kg_graph,
        )
        return res

    def _generate_sub_query_with_history_qa(self, history: List[LFPlan], sub_query):
        # Generate a sub-query with history qa pair
        if history:
            history_sub_answer = [
                h.res.sub_answer
                for h in history[:3]
                if "i don't know" not in h.res.sub_answer.lower()
            ]
            sub_query_with_history_qa = "\n".join(history_sub_answer) + "\n" + sub_query
        else:
            sub_query_with_history_qa = sub_query
        return sub_query_with_history_qa

    def atomic_queries_decomposition(self, query: str, history_context: List[str], **kwargs):
        try:
            while True:
                atomic_queries = self.llm_client.invoke(
                    {"query": query, "context": history_context},
                    self.decomposition_prompt,
                    with_except=False
                )
                if isinstance(atomic_queries, List):
                    return atomic_queries
        except Exception as e:
            print(f"Error in atomic_queries_decomposition: {str(e)}")
            return []

    def execute_with_aq(self, query, lf_nodes: List[LFPlan], max_iteration = 1, **kwargs) -> LFExecuteResult:
        iteration_count =0
        history_context = []
        while iteration_count < max_iteration:
            atomic_queries = self.atomic_queries_decomposition(query, "#".join(history_context))
            self._create_report_pipeline(kwargs.get("report_tool", None), query, lf_nodes)
            iteration_count += 1
            chosen_chunk = []
            for atomic_query in atomic_queries:
                doc_retrieved = self.atomic_question_retriever.recall_chunk_with_atomic_question(
                    queries=[atomic_query],
                    kwargs=self.params
                )
                chosen_chunk.extend(doc_retrieved)

            sorted_docs = sorted(chosen_chunk, key=lambda x: float(x.split("#")[-1]), reverse=True)
            pure_chunks = ["#".join(item.split("#")[:-1]) for item in sorted_docs]
            top_docs = []
            for item in pure_chunks:
                if item not in top_docs:
                    top_docs.append(item)
                if len(top_docs) == 10:
                    break
            history_context.extend(top_docs)

        generated_answer = self.generator.generate_sub_answer(query, [], history_context, [])

        result = LFExecuteResult()
        result.kg_exact_solved_answer = generated_answer
        result.recall_docs = history_context

        return result

    def execute(self, query, lf_nodes: List[LFPlan], **kwargs) -> LFExecuteResult:
        # execute_with_aq_flag = True
        execute_with_aq_flag = False
        max_iteration = 5

        if execute_with_aq_flag:
            return self.execute_with_aq(query, lf_nodes, max_iteration)
        process_info = {"kg_solved_answer": []}
        kg_graph = KgGraph()
        history = []
        # Process each sub-query.
        for idx, lf in enumerate(lf_nodes):
            sub_result = self._execute_lf(
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
            history.append(lf)
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
