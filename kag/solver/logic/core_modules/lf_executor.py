import logging
import os
import time
from typing import List

from kag.common.graphstore.graph_store import GraphStore
from kag.interface.retriever.chunk_retriever_abc import ChunkRetrieverABC
from kag.interface.retriever.kg_retriever_abc import KGRetrieverABC
from kag.solver.common.base import Question
from kag.solver.logic.core_modules.common.base_model import LFPlanResult
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.logic.core_modules.op_executor.op_deduce.deduce_executor import DeduceExecutor
from kag.solver.logic.core_modules.op_executor.op_math.math_executor import MathExecutor
from kag.solver.logic.core_modules.op_executor.op_output.output_executor import OutputExecutor
from kag.solver.logic.core_modules.op_executor.op_retrieval.retrieval_executor import RetrievalExecutor
from kag.solver.logic.core_modules.op_executor.op_sort.sort_executor import SortExecutor
from kag.solver.logic.core_modules.parser.logic_node_parser import ParseLogicForm
from kag.solver.logic.core_modules.retriver.entity_linker import EntityLinkerBase
from kag.solver.logic.core_modules.retriver.graph_retriver.dsl_executor import DslRunner, DslRunnerOnGraphStore
from kag.solver.logic.core_modules.retriver.schema_std import SchemaRetrieval
from kag.solver.logic.core_modules.rule_runner.rule_runner import OpRunner
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool

logger = logging.getLogger()


class LogicExecutor:
    def __init__(self, query: str, project_id: str,
                 schema: SchemaUtils, kg_retriever: KGRetrieverABC,
                 chunk_retriever: ChunkRetrieverABC, std_schema: SchemaRetrieval, el: EntityLinkerBase, generator,
                 dsl_runner: DslRunner,
                 text_similarity: TextSimilarity=None,
                 req_id='',
                 need_detail=False, llm=None, report_tool=None, params=None):
        """
        Initializes the LogicEngine with necessary parameters and configurations.

        :param query: The main query to process.
        :param project_id: Identifier for the project.
        :param schema: The schema used for processing.
        :chunk_retriever (ChunkRetriever): An instance for chunk-level retrieval. If not provided, we will not execute chunk retrieval.
        :kg_retriever (KGRetrieval): An instance for graph-level retrieval. If not provided, we will not execute retrieval on graph.
        :param std_schema: Standard schema retrieval instance for retrieval schema label.
        :param el: Entity linker base instance.
        :param generator: Generator for generating answers.
        :param dsl_runner: DSL runner instance, can run cypher to query graph. Defaults to `None`.
        :param text_similarity: convert text to vector, and compute similarity score
        :param req_id: Request identifier. Defaults to an empty string.
        :param need_detail: Flag indicating whether detailed information is needed. Defaults to `False`.
        :param llm: Language model instance. Defaults to `None`.
        :param report_tool: Reporting tool instance. Defaults to `None`.
        :param params: Additional parameters. Defaults to `None`.
        """
        # pipeline record
        if params is None:
            params = {}
        self.report_tool = report_tool
        self.need_detail = need_detail
        self.req_id = req_id
        self.params = params
        self.dsl_runner = dsl_runner
        self.schema = schema
        self.project_id = project_id
        self.nl_query = query
        self.query_one_graph_cache = {}
        self.kg_graph = KgGraph()
        self.kg_retriever = kg_retriever
        self.chunk_retriever = chunk_retriever
        self.alias_entity = {}
        self.query_schema = {}
        self.need_query_one_hop_with_rel = []
        self.recall_data_time = 0
        self.debug_info = {
            "el": [],
            "el_detail": [],
            "std_out": [],
            "get_empty": [],
            "sub_qa_pair": []
        }
        self.op_runner = OpRunner(self.kg_graph, llm, query, self.req_id)
        self.parser = ParseLogicForm(self.schema, std_schema)
        self.text_similarity = text_similarity or TextSimilarity()
        self.llm = llm
        self.generator = generator
        self.el = el

        self.force_chunk_retriever = os.getenv("KAG_QA_FORCE_CHUNK_RETRIEVER", False)

        # Initialize executors for different operations.
        self.retrieval_executor = RetrievalExecutor(query, self.kg_graph, self.schema, self.kg_retriever,
                                                    self.el,
                                                    self.dsl_runner, self.debug_info, text_similarity,KAG_PROJECT_ID = self.project_id)
        self.deduce_executor = DeduceExecutor(query, self.kg_graph, self.schema, self.op_runner, self.debug_info, KAG_PROJECT_ID = self.project_id)
        self.sort_executor = SortExecutor(query, self.kg_graph, self.schema, self.debug_info, KAG_PROJECT_ID = self.project_id)
        self.math_executor = MathExecutor(query, self.kg_graph, self.schema, self.debug_info, KAG_PROJECT_ID = self.project_id)
        self.output_executor = OutputExecutor(query, self.kg_graph, self.schema, self.el,
                                              self.dsl_runner,
                                              self.retrieval_executor.query_one_graph_cache, self.debug_info, KAG_PROJECT_ID = self.project_id)

        self.with_sub_answer = os.getenv("KAG_QA_WITH_SUB_ANSWER", True)

    def _convert_logic_nodes_2_question(self, logic_nodes: List[LFPlanResult]) -> List[Question]:
        ret_question = []
        for i in range(0, len(logic_nodes)):
            if i == 0:
                question = Question(
                    question=logic_nodes[i].query,
                )
            else:
                question = Question(
                    question=logic_nodes[i].query,
                    dependencies=[ret_question[i - 1]]
                )
            question.id = i
            ret_question.append(question)
        return ret_question

    def _generate_sub_answer(self, history: list, spo_retrieved: list, docs: list, sub_query: str):
        if not self.with_sub_answer:
            return "I don't know"
        return self.generator.generate_sub_answer(sub_query, spo_retrieved, docs, history)

    def execute(self, lf_nodes: List[LFPlanResult], init_query):
        """
        Executes the logic nodes and processes the initial query to retrieve answers.

        :param lf_nodes: List of logic nodes to be executed.
        :param init_query: The initial query that triggered this execution.
        :return: A tuple containing the QA results, knowledge graph, and execution history.
        """
        self._create_report_pipeline(init_query, lf_nodes)

        kg_qa_result = []
        history = []
        query_ner_list = {}
        # get NER results for the initial query, for chunk retrieve
        if self.chunk_retriever and hasattr(self.chunk_retriever, 'get_std_ner_by_query'):
            query_ner_list = self.chunk_retriever.get_std_ner_by_query(init_query)

        query_num = 0

        # Process each sub-query.
        for lf in lf_nodes:
            sub_query, sub_logic_nodes = lf.query, lf.lf_nodes
            query_num += 1
            node_begin_time = time.time()
            sub_logic_nodes_str = "\n".join([str(ln) for ln in sub_logic_nodes])

            question = self._create_sub_question_report_node(query_num, sub_logic_nodes_str, sub_query)
            if self.kg_retriever:
                kg_qa_result, spo_retrieved = self._execute_lf(sub_logic_nodes)
            else:
                logger.info(f"lf executor disabled kg retriever {init_query}")
                kg_qa_result, spo_retrieved = [], []

            question.context.append(f"#### spo retrieved:")
            question.context.append(f"{spo_retrieved if len(spo_retrieved) > 0 else 'no spo tuple retrieved'}.")
            self._update_sub_question_status(question, None, ReporterIntermediateProcessTool.STATE.RUNNING)


            answer_source = "spo"
            docs_with_score = []
            all_related_entities, sub_answer = self._generate_sub_answer_by_graph(
                history, kg_qa_result, spo_retrieved, sub_query)

            # if sub answer is `I don't know`, we use chunk retriever
            if "i don't know" in sub_answer.lower() and self.chunk_retriever:
                answer_source = "chunk"
                question.context.append(f"## Chunk Retriever")
                self._update_sub_question_status(question, None, ReporterIntermediateProcessTool.STATE.RUNNING)

                start_time = time.time()
                # Update parameters to include retrieved SPO entities as starting points for chunk retrieval.
                params = {
                    'related_entities': all_related_entities,
                    'query_ner_dict': query_ner_list,
                    'req_id': self.req_id
                }
                # Retrieve chunks using the updated parameters.
                sub_query_with_history_qa = self._generate_sub_query_with_history_qa(history, sub_query)
                docs_with_score = self.chunk_retriever.recall_docs(sub_query_with_history_qa, top_k=10, **params)
                docs = ["#".join(item.split("#")[:-1]) for item in docs_with_score]

                self._update_sub_question_recall_docs(docs, question)
                self._update_sub_question_status(question, None, ReporterIntermediateProcessTool.STATE.RUNNING)

                retrival_time = time.time() - start_time
                sub_answer = self._generate_sub_answer(history, spo_retrieved, docs, sub_query)
                question.context.append("#### answer based by fuzzy retrieved:")
                question.context.append(f"{sub_answer}")
                logger.info(f"{self.req_id} call by docs cost: {retrival_time} docs num={len(docs)}")

            history.append(
                {"sub_query": sub_query, "sub_answer": sub_answer, 'docs': docs_with_score,
                 'spo_retrieved': spo_retrieved,
                 'exactly_match': self.debug_info.get('exact_match_spo', False),
                 'logic_expr': sub_logic_nodes_str, 'answer_source': answer_source,
                 'cost': time.time() - node_begin_time})
            self.debug_info['sub_qa_pair'].append([sub_query, sub_answer])
            self._update_sub_question_status(question, sub_answer, ReporterIntermediateProcessTool.STATE.FINISH)

        return kg_qa_result, self.kg_graph, history

    def _generate_sub_query_with_history_qa(self, history, sub_query):
        # Generate a sub-query with history qa pair
        if history:
            history_sub_answer = [h['sub_answer'] for h in history[:3] if
                                  "i don't know" not in h['sub_answer'].lower()]
            sub_query_with_history_qa = '\n'.join(history_sub_answer) + '\n' + sub_query
        else:
            sub_query_with_history_qa = sub_query
        return sub_query_with_history_qa

    def _update_sub_question_recall_docs(self, docs, question):
        question.context.extend(["|id|content|", "|-|-|"])
        for i, d in enumerate(docs, start=1):
            _d = d.replace('\n', '<br>')
            question.context.append(f"|{i}|{_d}|")

    def _generate_sub_answer_by_graph(self, history, kg_qa_result, spo_retrieved, sub_query):
        sub_answer = "I don't know"
        all_related_entities = self.kg_graph.get_all_entity()
        all_related_entities = list(set(all_related_entities))
        if self.force_chunk_retriever:
            # if this flag is true, we force use chunk retriever
            logger.info(f"lf executor disabled with_sub_answer {sub_query}")
            return all_related_entities, sub_answer
        # if spo retrieved empty, we use chunk retriever to retrieve answer
        if len(spo_retrieved) == 0 and len(kg_qa_result) == 0:
            all_related_entities = []
        # if there is answer in kg_qa_result, and the answer is exact match with spo, we generate answer with kg result
        elif self.debug_info.get('exact_match_spo', False):
            if len(kg_qa_result) > 0:
                sub_answer = str(kg_qa_result)
            else:
                sub_answer = str(spo_retrieved)
        # other condition, we generate answer by graph, if can not generate answer, we will return `I don't know`
        else:
            if len(spo_retrieved) == 0:
                spo_retrieved = kg_qa_result
            sub_answer = self._generate_sub_answer(history, spo_retrieved, [], sub_query)
        return all_related_entities, sub_answer

    def _update_sub_question_status(self, question, answer, status):
        if self.report_tool:
            self.report_tool.report_node(question, answer, status)

    def _create_sub_question_report_node(self, query_num, sub_logic_nodes_str, sub_query):
        question = Question(
            question=sub_query,
        )
        question.id = query_num
        question.context = ["## SPO Retriever", "#### logic_form expression: ",
                            f'```java\n{sub_logic_nodes_str}\n```']
        if self.report_tool:
            self.report_tool.report_node(question, None, ReporterIntermediateProcessTool.STATE.RUNNING)
        return question

    def _create_report_pipeline(self, init_query, lf_nodes):
        if self.report_tool:
            self.report_tool.report_pipeline(Question(question=init_query), self._convert_logic_nodes_2_question(lf_nodes))

    def _execute_lf(self, sub_logic_nodes):
        kg_qa_result = []
        spo_set = []
        # Execute graph retrieval operations.
        for n in sub_logic_nodes:
            logger.debug(f"{self.req_id} begin run logic node " + str(n))
            if self.retrieval_executor.is_this_op(n):
                self.retrieval_executor.executor(n, self.req_id, self.params)
                cur_spo_set = self.kg_graph.get_entity_by_alias(n.p.alias_name)
                if cur_spo_set is not None and len(cur_spo_set) > 0:
                    spo_set += [str(spo) for spo in cur_spo_set]
            elif self.deduce_executor.is_this_op(n):
                deduce_res = self.deduce_executor.executor(n, self.req_id, self.params)
                if isinstance(deduce_res, list):
                    kg_qa_result += deduce_res
            elif self.math_executor.is_this_op(n):
                self.math_executor.executor(n, self.req_id, self.params)
            elif self.sort_executor.is_this_op(n):
                self.sort_executor.executor(n, self.req_id, self.params)
            elif self.output_executor.is_this_op(n):
                kg_qa_result += self.output_executor.executor(n, self.req_id, self.params)
            else:
                logger.warning(f"unknown operator: {n.operator}")
        return kg_qa_result, spo_set
