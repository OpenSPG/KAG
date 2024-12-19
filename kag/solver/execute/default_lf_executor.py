import logging
from typing import List

from kag.interface.solver.execute.lf_executor_abc import LFExecutorABC
from kag.interface.solver.execute.lf_sub_query_merger_abc import LFSubQueryResMerger
from kag.solver.execute.op_executor.op_deduce.deduce_executor import DeduceExecutor
from kag.solver.execute.op_executor.op_math.math_executor import MathExecutor
from kag.solver.execute.op_executor.op_output.output_executor import OutputExecutor
from kag.solver.execute.op_executor.op_retrieval.retrieval_executor import RetrievalExecutor
from kag.solver.execute.op_executor.op_sort.sort_executor import SortExecutor
from kag.solver.execute.sub_query_generator import LFSubGenerator
from kag.interface.solver.base_model import LFExecuteResult, LFPlan, SubQueryResult
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.utils import generate_random_string
from kag.solver.retriever.chunk_retriever import ChunkRetriever
from kag.solver.retriever.exact_kg_retriever import ExactKgRetriever
from kag.solver.retriever.fuzzy_kg_retriever import FuzzyKgRetriever

logger = logging.getLogger()


@LFExecutorABC.register("base", as_default=True)
class DefaultLFExecutor(LFExecutorABC):
    def __init__(self, exact_kg_retriever: ExactKgRetriever, fuzzy_kg_retriever: FuzzyKgRetriever,
                 chunk_retriever: ChunkRetriever, merger: LFSubQueryResMerger,
                 **kwargs):
        super().__init__(**kwargs)

        self.params = kwargs

        # tmp graph data
        self.schema: SchemaUtils = kwargs.get("schema", None)
        self.process_info = {}

        self.exact_kg_retriever = exact_kg_retriever
        self.fuzzy_kg_retriever = fuzzy_kg_retriever
        self.chunk_retriever = chunk_retriever
        self.params['exact_kg_retriever'] = exact_kg_retriever
        self.params['fuzzy_kg_retriever'] = fuzzy_kg_retriever
        self.params['chunk_retriever'] = chunk_retriever

        # Generate
        self.generator = LFSubGenerator()

        self.merger: LFSubQueryResMerger = merger or LFSubQueryResMerger.from_config({
            "type": "base"
        })

        # Initialize executors for different operations.
        self.retrieval_executor = RetrievalExecutor(schema=self.schema,
                                                    **self.params)
        self.deduce_executor = DeduceExecutor(schema=self.schema,
                                              **self.params)
        self.sort_executor = SortExecutor(schema=self.schema,
                                          **self.params)
        self.math_executor = MathExecutor(schema=self.schema,
                                          **self.params)
        self.output_executor = OutputExecutor(schema=self.schema,
                                              **self.params)

    def _judge_sub_answered(self, sub_answer: str):
        return sub_answer and "i don't know" not in sub_answer.lower()

    def _execute_lf(self, req_id: str, query: str, sub_query: LFPlan, process_info: dict,
                    kg_graph: KgGraph) -> SubQueryResult:

        res = SubQueryResult()
        res.sub_query = sub_query
        process_info[sub_query.query] = {
            'spo_retrieved': [],
            'doc_retrieved': [],
            'match_type': 'chunk',
            'kg_answer': '',
        }
        # Execute graph retrieval operations.
        for n in sub_query.lf_nodes:
            if self.retrieval_executor.is_this_op(n):
                self.retrieval_executor.executor(query, n, req_id, kg_graph, process_info, self.params)
            elif self.deduce_executor.is_this_op(n):
                self.deduce_executor.executor(query, n, req_id, kg_graph, process_info, self.params)
            elif self.math_executor.is_this_op(n):
                self.math_executor.executor(query, n, req_id, kg_graph, process_info, self.params)
            elif self.sort_executor.is_this_op(n):
                self.sort_executor.executor(query, n, req_id, kg_graph, process_info, self.params)
            elif self.output_executor.is_this_op(n):
                self.output_executor.executor(query, n, req_id, kg_graph, process_info, self.params)
            else:
                logger.warning(f"unknown operator: {n.operator}")

        res.spo_retrieved = process_info[sub_query].get('spo_retrieved', [])
        res.doc_retrieved = process_info[sub_query].get('doc_retrieved', [])
        res.match_type = process_info[sub_query].get('match_type', 'chunk')
        kg_answer = process_info[sub_query]['kg_answer']
        # generate sub answer
        if not self._judge_sub_answered(kg_answer):
            # generate sub answer
            sub_answer = self.generator.generate_sub_answer(sub_query.query, res.spo_retrieved, res.doc_retrieved,
                                                            self.history)
        else:
            sub_answer = kg_answer
        res.sub_answer = sub_answer
        return res

    def execute(self, query, lf_nodes: List[LFPlan]) -> LFExecuteResult:
        process_info = {
            'kg_solved_answer': []
        }
        kg_graph = KgGraph()
        history = []
        # Process each sub-query.
        for lf in lf_nodes:
            sub_result = self._execute_lf(generate_random_string(10), query, lf, process_info, kg_graph)
            lf.res = sub_result
            history.append(lf)
        # merge all results
        res = self.merger.merge(query, history)
        res.retrieved_kg_graph = kg_graph
        res.kg_exact_solved_answer = process_info['kg_solved_answer']
        return res
