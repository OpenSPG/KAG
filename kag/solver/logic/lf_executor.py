import logging
import time
from typing import List
from enum import Enum

from kag.common.graphstore.graph_store import GraphStore
from kag.interface.retriever.chunk_retriever_abc import ChunkRetrieverABC
from kag.interface.retriever.kg_retriever_abc import KGRetrieverABC
from kag.solver.common.base import Question
from kag.solver.logic.common.base_model import LogicNode, LFPlanResult
from kag.solver.logic.common.one_hop_graph import KgGraph
from kag.solver.logic.common.schema import Schema
from kag.solver.logic.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.config import LogicFormConfiguration
from kag.solver.logic.dsl_generator import DslGenerator
from kag.solver.logic.op_executor.op_deduce.deduce_executor import DeduceExecutor
from kag.solver.logic.op_executor.op_math.math_executor import MathExecutor
from kag.solver.logic.op_executor.op_output.output_executor import OutputExecutor
from kag.solver.logic.op_executor.op_retrieval.retrieval_executor import RetrievalExecutor
from kag.solver.logic.op_executor.op_sort.sort_executor import SortExecutor
from kag.solver.logic.parser.logic_node_parser import ParseLogicForm
from kag.solver.logic.retriver.entity_linker import EntityLinkerBase
from kag.solver.logic.retriver.graph_retriver.dsl_executor import DslRunnerOnGraphStore, \
    DslRunner
from kag.solver.logic.retriver.schema_std import SchemaRetrieval
from kag.solver.logic.rule_runner.rule_runner import OpRunner

logger = logging.getLogger()


class STATE(str, Enum):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    FINISH = "FINISH"
    ERROR = "ERROR"


class LogicExecutor:
    def __init__(self, query: str, project_id: str,
                 schema: Schema, kg_retriever: KGRetrieverABC,
                 chunk_retriever: ChunkRetrieverABC, std_schema: SchemaRetrieval, el: EntityLinkerBase,
                 graph_store: GraphStore, generator,
                 dsl_runner: DslRunner = None,
                 req_id='',
                 need_detail=False, llm=None, report_tool=None, params=None, force_chunk_retriever = False):
        """
        Initializes the LogicEngine with necessary parameters and configurations.

        :param query: The main query to process.
        :param project_id: Identifier for the project.
        :param schema: The schema used for processing.
        :chunk_retriever (ChunkRetriever): An instance for chunk-level retrieval. If not provided, we will not execute chunk retrieval.
        :kg_retriever (KGRetrieval): An instance for graph-level retrieval. If not provided, we will not execute retrieval on graph.
        :param std_schema: Standard schema retrieval instance for retrieval schema label.
        :param el: Entity linker base instance.
        :param graph_store: Graph store instance.
        :param generator: Generator for generating answers.
        :param dsl_runner: DSL runner instance, can run cypher to query graph. Defaults to `None`.
        :param req_id: Request identifier. Defaults to an empty string.
        :param need_detail: Flag indicating whether detailed information is needed. Defaults to `False`.
        :param llm: Language model instance. Defaults to `None`.
        :param report_tool: Reporting tool instance. Defaults to `None`.
        :param params: Additional parameters. Defaults to `None`.
        :param force_chunk_retriever: Flag to force chunk retriever usage. Defaults to `False`.
        """
        # pipeline record
        if params is None:
            params = {}
        self.report_tool = report_tool
        self.need_detail = need_detail
        self.req_id = req_id
        self.params = params
        if dsl_runner is None:
            self.dsl_runner = DslRunnerOnGraphStore(project_id, schema, LogicFormConfiguration({
                "project_id": project_id
            }), graph_store=graph_store)
        else:
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
            "get_empty": []
        }
        self.op_runner = OpRunner(self.kg_graph, llm, query, self.req_id)
        self.parser = ParseLogicForm(self.schema, std_schema)

        self.text_similarity = TextSimilarity()
        self.llm = llm
        self.generator = generator
        self.el = el

        self.force_chunk_retriever = force_chunk_retriever

    def get_graph_retrival_detail(self):
        """
        Retrieves detailed information about graph retrieval.

        :return: Dictionary containing graph retrieval details.
        """
        result = {}
        for k in self.query_one_graph_cache.keys():
            one_hop_graph = self.query_one_graph_cache[k]
            one_hop_detail = one_hop_graph.to_graph_detail()
            for s in one_hop_detail.keys():
                if s not in result.keys():
                    result[s] = one_hop_detail[s]
                else:
                    origin_s_info = result[s]
                    for t_k in one_hop_detail[s].keys():
                        if t_k not in origin_s_info.keys():
                            origin_s_info[t_k] = one_hop_detail[s][t_k]
                        else:
                            total_data = origin_s_info[t_k] + one_hop_detail[s][t_k]
                            try:
                                origin_s_info[t_k] = list(set(total_data))
                            except Exception as e:
                                logger.info(f"get_graph_retrival_detail except {e}", exc_info=True)
                    result[s] = origin_s_info
            result["start_node"] = self.kg_graph.start_node_name
        return result

    def prune_logic_nodes_plan(self, logic_nodes):
        """
        prune plan for logic nodes.

        :param logic_nodes: List of logic nodes.
        :return: Simplified logic nodes.
        """
        dsl_generator = DslGenerator(self.schema, True)
        logic_nodes = dsl_generator.prune_nodes(logic_nodes)
        logger.info(f"{self.req_id} pruned nodes " + str(logic_nodes))
        return logic_nodes

    def logic_querys_2_logic_nodes(self, logic_querys, sub_querys=None, question=None, init_query=None):
        """
        Converts logic queries into logic nodes.

        :param logic_querys: List of logic queries.
        :param sub_querys: List of sub-queries. Defaults to `None`.
        :param question: Main question. Defaults to `None`.
        :param init_query: Initial query. Defaults to `None`.
        :return: Parsed logic nodes.
        """
        if sub_querys is None:
            sub_querys = []
        return self.parser.parse_logic_form_set(logic_querys, sub_querys, question, init_query)

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

    def _split_sub_query(self, logic_nodes: List[LogicNode]):
        query_lf_map = {}
        for n in logic_nodes:
            if n.sub_query in query_lf_map.keys():
                query_lf_map[n.sub_query] = query_lf_map[n.sub_query] + [n]
            else:
                query_lf_map[n.sub_query] = [n]
        return query_lf_map

    def _get_history_info(self, history: list):
        if history:
            history_sub_answer = [h['sub_answer'] for h in history[:3] if "I don't know" not in h['sub_answer']]
        else:
            history_sub_answer = []
        return "\n".join(history_sub_answer)

    def _sub_graph_answer(self, history: list, spo_retrieved: list, sub_query: str):
        if len(spo_retrieved) == 0:
            return "I don't know"
        return self.generator.generate_sub_answer(sub_query, spo_retrieved, [], history)

    def execute(self, lf_nodes: List[LFPlanResult], init_query):
        """
        Executes the logic nodes and processes the initial query to retrieve answers.

        :param lf_nodes: List of logic nodes to be executed.
        :param init_query: The initial query that triggered this execution.
        :return: A tuple containing the QA results, knowledge graph, retrieval details, verification match results,
                 entity linking debug info, and execution history.
        """
        if self.report_tool:
            self.report_tool.report_pipeline(init_query, self._convert_logic_nodes_2_question(lf_nodes))
        kg_qa_result = []
        verify_match_res = None
        history = []

        # Initialize executors for different operations.
        retrieval_executor = RetrievalExecutor(  # GetSPOExecutor; SearchS[未实现]
            init_query, self.kg_graph, self.schema, self.kg_retriever, self.el, self.dsl_runner, self.debug_info
        )
        deduce_executor = DeduceExecutor(init_query, self.kg_graph, self.schema, self.op_runner, self.debug_info)
        sort_executor = SortExecutor(init_query, self.kg_graph, self.schema, self.debug_info)  # 空
        math_executor = MathExecutor(init_query, self.kg_graph, self.schema, self.debug_info)  # 空
        output_executor = OutputExecutor(  # GetExecutor
            init_query, self.kg_graph, self.schema, self.el,
            self.dsl_runner, retrieval_executor.query_one_graph_cache, self.debug_info
        )

        query_num = 0

        # Process each sub-query.
        for lf in lf_nodes:
            sub_query, sub_logic_nodes = lf.query, lf.lf_nodes
            query_num += 1
            node_begin_time = time.time()

            question = Question(question=sub_query,)
            question.id = query_num
            sub_logic_nodes_str = "\n".join([str(ln) for ln in sub_logic_nodes])
            question.context = [
                "## SPO Retriever", "#### logic_form expression: ",
                f'```java\n{sub_logic_nodes_str}\n```'
            ]
            if self.report_tool:
                self.report_tool.report_node(question, None, STATE.RUNNING)

            spo_set = []
            kg_qa_result = []
            # Execute graph retrieval operations.
            for n in sub_logic_nodes:
                logger.debug(f"{self.req_id} begin run logic node " + str(n))
                if retrieval_executor.is_this_op(n):
                    retrieval_executor.executor(n, self.req_id, self.params)
                    cur_spo_set = self.kg_graph.get_entity_by_alias(n.p.alias_name)
                    if cur_spo_set is not None and len(cur_spo_set) > 0:
                        spo_set += cur_spo_set
                elif deduce_executor.is_this_op(n):
                    deduce_executor.executor(n, self.req_id, self.params)
                elif math_executor.is_this_op(n):
                    math_executor.executor(n, self.req_id, self.params)
                elif sort_executor.is_this_op(n):
                    sort_executor.executor(n, self.req_id, self.params)
                elif output_executor.is_this_op(n):
                    kg_qa_result = output_executor.executor(n, self.req_id, self.params)
                else:
                    logger.warning(f"unknown operator: {n.operator}")

            spo_retrieved = spo_set

            if self.report_tool:
                self.report_tool.report_node(question, None, STATE.RUNNING)
            if len(spo_retrieved) > 0:
                spo_retrieved = [str(spo) for spo in spo_retrieved]
            question.context.append(f"#### spo retrieved:")
            question.context.append(f"{spo_retrieved if len(spo_retrieved) > 0 else 'no spo tuple retrieved'}.")

            # Generate a sub-query with history qa pair
            if history:
                history_sub_answer = [h['sub_answer'] for h in history[:3] if "i don't know" not in h['sub_answer'].lower()]
                sub_query_with_history_qa = '\n'.join(history_sub_answer) + '\n' + sub_query
            else:
                sub_query_with_history_qa = sub_query

            all_related_entities = self.kg_graph.get_all_entity()
            all_related_entities = list(set(all_related_entities))
            docs_with_score = []
            answer_source = "spo"

            # if spo retrieved empty, we use chunk retriever to retrieve answer
            if len(spo_retrieved) == 0:
                sub_answer = "I don't know"
                all_related_entities = []
            # if there is answer in kg_qa_result, and the answer is exact match with spo, we use kg_qa_result
            elif len(kg_qa_result) > 0 and self.debug_info.get('exact_match_spo', False):
                sub_answer = ",".join(kg_qa_result)
            # if this flag is true, we force use chunk retriever
            elif self.force_chunk_retriever:
                sub_answer = "I don't know"
            # other condition, we generate answer by graph, if can not generate answer, we will return `I don't know`
            else:
                sub_answer = self._sub_graph_answer(history, spo_retrieved, sub_query)

            # if sub answer is `I don't know`, we use chunk retriever
            if "i don't know" in sub_answer.lower():
                answer_source = "chunk"
                question.context.append(f"## Chunk Retriever")
                if self.report_tool:
                    self.report_tool.report_node(question, None, STATE.RUNNING)

                start_time = time.time()
                query_ner_list = {}
                # get NER results for the initial query, for chunk retrieve
                if hasattr(self.chunk_retriever, 'get_std_ner_by_query'):
                    query_ner_list = self.chunk_retriever.get_std_ner_by_query(init_query)
                # Update parameters to include retrieved SPO entities as starting points for chunk retrieval.
                params = {
                    'el_res': self.debug_info['el'],
                    'related_entities': all_related_entities,
                    'query_ner_dict': query_ner_list,
                    'req_id': self.req_id
                }
                # Retrieve chunks using the updated parameters.
                docs_with_score = self.chunk_retriever.recall_docs(sub_query_with_history_qa, top_k=10, **params)
                docs = ["#".join(item.split("#")[:-1]) for item in docs_with_score]
                retrival_time = time.time() - start_time
                question.context.extend(["|id|content|", "|-|-|"])
                for i, d in enumerate(docs, start=1):
                    _d = d.replace('\n', '<br>')
                    question.context.append(f"|{i}|{_d}|")
                if self.report_tool:
                    self.report_tool.report_node(question, None, STATE.RUNNING)

                sub_answer = self.generator.generate_sub_answer(sub_query, spo_retrieved, docs, history)
                question.context.append("#### answer based by fuzzy retrieved:")
                question.context.append(f"{sub_answer}")
                logger.info(f"{self.req_id} call by docs cost: {retrival_time} docs num={len(docs)}")

            history.append(
                {"sub_query": sub_query, "sub_answer": sub_answer, 'docs': docs_with_score, 'spo_retrieved': spo_retrieved,
                 'logic_expr': sub_logic_nodes_str, 'answer_source': answer_source,
                 'cost': time.time() - node_begin_time})
            if self.report_tool:
                self.report_tool.report_node(question, sub_answer, STATE.FINISH)

        return (
            kg_qa_result, self.kg_graph, self.get_graph_retrival_detail(), 
            verify_match_res, self.debug_info['el'], history
        )
