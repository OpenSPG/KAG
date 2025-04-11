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
from kag.solver.logic.core_modules.common.one_hop_graph import (
    AtomRetrievalInfo,
    KgGraph,
)
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
        atomic_query_decomposition_prompt: PromptABC = None,
        atomic_question_selection_prompt: PromptABC = None,
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

        self.atomic_query_decomposition_prompt = atomic_query_decomposition_prompt
        self.atomic_question_selection_prompt = atomic_question_selection_prompt
        biz_scene = KAG_PROJECT_CONF.biz_scene
        if self.atomic_query_decomposition_prompt is None:
            self.atomic_query_decomposition_prompt = init_prompt_with_fallback("atomic_query_decomposition_prompt", biz_scene)
        if self.atomic_question_selection_prompt is None:
            self.atomic_question_selection_prompt = init_prompt_with_fallback("atomic_question_selection_prompt", biz_scene)
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
            doc_retrieved, _ = self.atomic_question_retriever.recall_chunk_with_atomic_question(
                queries=sub_query,
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
            # res = self._execute_atomic_question_answer_with_embedding(
            #     req_id, query, lf, process_info, kg_graph, history, res
            # )
            res = self._execute_chunk_answer(
                req_id, query, lf, process_info, kg_graph, history, res
            )

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

    def atomic_queries_decomposition(self, query: str, history_context: str, **kwargs):
        try:
            retry_time = 0
            while retry_time < 3:
                thinking, atomic_queries = self.llm_client.invoke(
                    {"query": query, "context": history_context},
                    self.atomic_query_decomposition_prompt,
                    with_except=False
                )
                retry_time += 1
                if thinking != "llm error":
                    return thinking, atomic_queries
        except Exception as e:
            print(f"Error in atomic_queries_decomposition: {str(e)} of #{query}#")
            return "llm failure",[]

    def recall_atomic_chunk(self, atomic_query):
        _, atomic_chunk_pairs = self.atomic_question_retriever.recall_chunk_with_atomic_question(
            queries=atomic_query,
            kwargs=self.params,
        )
        return atomic_chunk_pairs

    def atomic_infos_to_context_string(self, chosen_atomic_infos: List[AtomRetrievalInfo], limit: int=80000) -> str:
        context: str = ""

        chunk_id_set = set()
        for info in chosen_atomic_infos:
            if info.chunk_id in chunk_id_set:
                continue
            chunk_id_set.add(info.chunk_id)

            if info.title is not None:
                context += f"\nTitle: {info.title}. Content: {info.content}\n"
            else:
                context += f"\n{info.content}\n"

            if len(context) >= limit:
                break

        context = context.strip()
        return context

    def select_suitable_chunk(self, ori_query, atomic_info_candidates, chosen_contexts: List[AtomRetrievalInfo]) -> List[AtomRetrievalInfo]:
        num_atomics = len(atomic_info_candidates)
        chosen_context_str = self.atomic_infos_to_context_string(chosen_contexts)
        atomic_list_str = ""
        for i, info in enumerate(atomic_info_candidates):
            atomic_list_str += f"Question {i + 1}: {info.atomic}\n"

        thinking, question_idxs = self.llm_client.invoke(
            {"query": ori_query, "num_atoms":num_atomics, "chosen_context": chosen_context_str, "aq_list_str": atomic_list_str},
            self.atomic_question_selection_prompt,
            with_except=False
        )
        # if question_idx is not None and question_idx > 0 and question_idx <= len(atomic_info_candidates):
        #     chosen_info = atomic_info_candidates[question_idx - 1]
        #     return chosen_info
        chosen_info = []
        if len(question_idxs):
            for question_idx in question_idxs:
                if question_idx > 0 and question_idx <= len(atomic_info_candidates):
                    chosen_info.append(atomic_info_candidates[question_idx - 1])
            return chosen_info
        else:
            return []

    def atomic_info_to_lf_history(self, chosen_contexts: List[AtomRetrievalInfo]) -> List[LFPlan]:
        history = []
        for info in chosen_contexts:
            aq = LFPlan(info.atomic,[])
            res = SubQueryResult()
            res.sub_query = aq.query
            res.doc_retrieved.append(f"#{info.title}#{info.content}#{info.score}")
            res.spo_retrieved = []
            res.match_type = "atomic query"
            res.sub_answer = self.generator.generate_sub_answer(
                aq.query, res.spo_retrieved, res.doc_retrieved, history
            )
            aq.res = res
            history.append(aq)
        return history

    def execute_with_aq(self, query, max_iteration = 1, **kwargs):
        iteration_count =0
        process_info = {"kg_solved_answer": []}
        chosen_contexts: List[AtomRetrievalInfo] = []

        while iteration_count < max_iteration:
            chosen_context_str = self.atomic_infos_to_context_string(chosen_contexts) if len(chosen_contexts) > 0 else ""
            # Step 1: Let LLM client provide a decomposition proposal with current context.
            thinking, atomic_queries = self.atomic_queries_decomposition(query, chosen_context_str)

            if len(atomic_queries) == 0 and thinking != "llm failure":
                break
            if thinking == "llm failure":
                continue

            # self._create_report_pipeline(kwargs.get("report_tool", None), query, [])
            iteration_count += 1

            # Step 2: Retrieve relevant atom information to the sub-question proposals.
            atomic_info_candidates = []
            for atomic_query in atomic_queries:
                atomic_chunks = self.recall_atomic_chunk(atomic_query)

                for atomic_chunk in atomic_chunks:
                    atomic_info_candidate = AtomRetrievalInfo(
                        atomic_query = atomic_query,
                        atomic = atomic_chunk['atomic_question_name'],
                        chunk_id= atomic_chunk['chunk_id'],
                        content= atomic_chunk['chunk_content'],
                        title= atomic_chunk['chunk_name'],
                        score= atomic_chunk['score'],
                    )
                    atomic_info_candidates.append(atomic_info_candidate)

            #Step 3: Choice related history atomic question answer
            chosen_atomic_info = self.select_suitable_chunk(query, atomic_info_candidates, chosen_contexts)
            chosen_contexts.extend(chosen_atomic_info)

        history = self.atomic_info_to_lf_history(chosen_contexts)
        return history

        # Last Step: Let LLM client answer the original question with all chosen atom information during the loop above.
        # res = self.merger.merge(query, history)
        # res.retrieved_kg_graph = KgGraph()
        # res.kg_exact_solved_answer = ""
        # return res

    def execute(self, query, lf_nodes: List[LFPlan], **kwargs) -> LFExecuteResult:
        execute_with_aq_flag = True
        # execute_with_aq_flag = False
        max_iteration = 5
        history = []

        if execute_with_aq_flag:
            history.extend(self.execute_with_aq(query, max_iteration))

        process_info = {"kg_solved_answer": []}
        kg_graph = KgGraph()
        # Process each sub-query.
        # for idx, lf in enumerate(lf_nodes):
        #     sub_result = self._execute_lf(
        #         req_id=generate_random_string(10),
        #         index=idx + 1,
        #         query=query,
        #         lf=lf,
        #         process_info=process_info,
        #         kg_graph=kg_graph,
        #         history=history,
        #         **kwargs,
        #     )
        #     lf.res = sub_result
        #     history.append(lf)

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
