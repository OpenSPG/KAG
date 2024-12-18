import logging
import time
from typing import List

from kag.interface.solver.execute.lf_executor_abc import LFExecutorABC
from kag.interface.solver.execute.lf_sub_query_merger_abc import LFSubQueryResMerger
from kag.solver.execute.op_executor.op_deduce.deduce_executor import DeduceExecutor
from kag.solver.execute.op_executor.op_math.math_executor import MathExecutor
from kag.solver.execute.op_executor.op_output.output_executor import OutputExecutor
from kag.solver.execute.op_executor.op_retrieval.retrieval_executor import RetrievalExecutor
from kag.solver.execute.op_executor.op_sort.sort_executor import SortExecutor
from kag.solver.execute.sub_query_generator import LFSubGenerator
from kag.solver.logic.core_modules.common.base_model import LFExecuteResult, LFPlan, LogicNode, SubQueryResult
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.retriever.chunk_retriever import ChunkRetriever
from kag.solver.retriever.exact_kg_retriever import ExactKgRetriever
from kag.solver.retriever.fuzzy_kg_retriever import FuzzyKgRetriever

logger = logging.getLogger()


class DefaultLFExecutor(LFExecutorABC):
    def __init__(self, req_id: str, **kwargs):
        super().__init__(**kwargs)
        self.req_id = req_id
        self.params = kwargs

        # tmp graph data
        self.kg_graph = KgGraph()
        self.schema: SchemaUtils = kwargs.get("schema", None)
        self.process_info = {}

        # Initialize executors for different operations.
        self.retrieval_executor = RetrievalExecutor(kg_graph=self.kg_graph, schema=self.schema,
                                                    process_info=self.process_info, kwargs=kwargs)
        self.deduce_executor = DeduceExecutor(kg_graph=self.kg_graph, schema=self.schema, process_info=self.process_info,
                                              kwargs=kwargs)
        self.sort_executor = SortExecutor(kg_graph=self.kg_graph, schema=self.schema, process_info=self.process_info,
                                          kwargs=kwargs)
        self.math_executor = MathExecutor(kg_graph=self.kg_graph, schema=self.schema, process_info=self.process_info,
                                          kwargs=kwargs)
        self.output_executor = OutputExecutor(kg_graph=self.kg_graph, schema=self.schema, process_info=self.process_info,
                                              kwargs=kwargs)

        # Generate
        self.generator = LFSubGenerator()

        self.history: List[SubQueryResult] = []

        self.merger: LFSubQueryResMerger = LFSubQueryResMerger.from_config({
            "type": kwargs.get("merger", "base")
        })

    def _judge_sub_answered(self, sub_answer: str):
        return sub_answer and "i don't know" not in sub_answer.lower()

    def _execute_lf(self, query: str, sub_query: LFPlan) -> SubQueryResult:
        res = SubQueryResult()
        res.logic_nodes = sub_query.lf_nodes
        res.sub_query = sub_query
        self.process_info[sub_query.query] = {
            'spo_retrieved': [],
            'doc_retrieved': [],
            'match_type': 'chunk',
            'kg_answer': '',
        }
        """
        Query: 张三的老婆名字是李四吗？
        Query1: 张三的老婆的名字是什么
        Action1: get_spo(s=s1:Person[张三], p=p1:老婆, o=o1:Person)
        Action2: get_spo(s=o1, p=p2:名字, o=o2:文本)
        Action3: get(o2)
        
        Query2: 
        """
        # Execute graph retrieval operations.
        for n in sub_query.lf_nodes:
            if self.retrieval_executor.is_this_op(n):
                self.retrieval_executor.executor(query, n, self.req_id, self.params)
            elif self.deduce_executor.is_this_op(n):
                self.deduce_executor.executor(query, n, self.req_id, self.params)
            elif self.math_executor.is_this_op(n):
                self.math_executor.executor(query, n, self.req_id, self.params)
            elif self.sort_executor.is_this_op(n):
                self.sort_executor.executor(query, n, self.req_id, self.params)
            elif self.output_executor.is_this_op(n):
                self.output_executor.executor(query, n, self.req_id, self.params)
            else:
                logger.warning(f"unknown operator: {n.operator}")

        res.spo_retrieved = self.process_info[sub_query].get('spo_retrieved', [])
        res.doc_retrieved = self.process_info[sub_query].get('doc_retrieved', [])
        res.match_type = self.process_info[sub_query].get('match_type', 'chunk')
        kg_answer = self.process_info[sub_query]['kg_answer']
        # generate sub answer
        if not self._judge_sub_answered(kg_answer):
            # generate sub answer
            sub_answer = self.generator.generate_sub_answer(sub_query.query, res.spo_retrieved, res.doc_retrieved, self.history)
        else:
            sub_answer = kg_answer
        res.sub_answer = sub_answer
        return res

    def execute(self, query, lf_nodes: List[LFPlan]) -> LFExecuteResult:

        # Process each sub-query.
        for lf in lf_nodes:
            node_begin_time = time.time()
            sub_query, sub_logic_nodes = lf.query, lf.lf_nodes
            sub_result = self._execute_lf(query, sub_query, sub_logic_nodes)
            self.history.append(sub_result)
        # merge all results
        res = self.merger.merge(query, self.history)
        res.retrieved_kg_graph = self.kg_graph
        return res
