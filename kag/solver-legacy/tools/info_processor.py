import json
import logging
import re
from enum import Enum
from typing import List

from kag.interface.solver.base_model import LFPlan, SubQueryResult
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph, EntityData
from knext.common.rest import ApiClient, Configuration
from knext.reasoner.rest.models.ca_pipeline import CaPipeline
from knext.reasoner.rest.models.data_edge import DataEdge
from knext.reasoner.rest.models.data_node import DataNode
from knext.reasoner.rest.models.edge import Edge
from knext.reasoner.rest.models.node import Node
from knext.reasoner.rest.models.report_pipeline_request import ReportPipelineRequest
from knext.reasoner.rest.models.sub_graph import SubGraph
from knext.reasoner.rest.reasoner_api import ReasonerApi

logger = logging.getLogger(__name__)


class ReporterIntermediateProcessTool:
    """
    A tool for reporting intermediate processes in a reasoning pipeline.

    Attributes:
        STATE (Enum): An enumeration of possible states for nodes in the pipeline.
        ROOT_ID (int): The root node ID.
        report_log (bool): Whether to report logs.
        task_id (str): The task ID.
        project_id (str): The project ID.
        client (ReasonerApi): API client for interacting with the reasoner.
        cur_node_id (int): Current node ID.
        last_sub_question_size (int): Size of the last sub-question list.
        sub_query_node (list): List of sub-query nodes.
        start_node_id (int): Starting node ID.
        create_pipeline_times (int): Number of times the pipeline has been created.
        language (str): Language for output messages.
    """

    class STATE(str, Enum):
        """Enumeration of possible states for nodes in the pipeline."""

        WAITING = "WAITING"
        RUNNING = "RUNNING"
        FINISH = "FINISH"
        ERROR = "ERROR"

    ROOT_ID = 0

    def __init__(
        self,
        report_log=False,
        task_id=None,
        project_id=None,
        host_addr=None,
        language="en",
    ):
        """
        Initialize the ReporterIntermediateProcessTool.

        Args:
            report_log (bool): Whether to report logs.
            task_id (str): The task ID.
            project_id (str): The project ID.
            host_addr (str): Host address for the API client.
            language (str): Language for output messages.
        """
        self.report_log = report_log
        self.task_id = task_id
        self.project_id = project_id
        self.client: ReasonerApi = ReasonerApi(
            api_client=ApiClient(configuration=Configuration(host=host_addr))
        )
        self.cur_node_id = self.ROOT_ID
        self.last_sub_question_size = self.ROOT_ID
        self.sub_query_node = []
        self.start_node_id = 1
        self.create_pipeline_times = 0
        self.language = language

    def get_start_node_name(self):
        """
        Get the name for the start node based on the current pipeline creation count.

        Returns:
            str: Name for the start node.
        """
        start_node_name = "问题" if self.language == "zh" else "Question"
        if self.create_pipeline_times != 0:
            start_node_name = (
                "反思问题" if self.language == "zh" else "Reflective Questioning"
            )
        return start_node_name

    def get_end_node_name(self):
        """
        Get the name for the end node.

        Returns:
            str: Name for the end node.
        """
        return "问题答案" if self.language == "zh" else "Answer"

    def get_sub_question_name(self, index):
        """
        Get the name for a sub-question node.

        Args:
            index (int): Index of the sub-question.

        Returns:
            str: Name for the sub-question node.
        """
        return f"子问题{index}" if self.language == "zh" else f"Sub Question {index}"

    def report_pipeline(self, question, rewrite_question_list: List[LFPlan] = []):
        """
        Report the entire pipeline including nodes and edges.

        Args:
            question (str): The original question.
            rewrite_question_list (List[LFPlan]): List of rewritten questions.
        """
        pipeline = CaPipeline()
        pipeline.nodes = []
        pipeline.edges = []
        self.cur_node_id += self.last_sub_question_size
        rethink_question = question
        # print(question)
        for idx, item in enumerate(rewrite_question_list, start=self.cur_node_id + 2):
            item.id = self.cur_node_id + idx

        if len(self.sub_query_node) == 0:
            end_node = Node(
                id=self.ROOT_ID,
                state=self.STATE.WAITING,
                question=rethink_question,
                answer=None,
                title=self.get_end_node_name(),
                logs=None,
            )
            self.sub_query_node.append(end_node)
            self.start_node_id = 1
        else:
            self.start_node_id = len(self.sub_query_node)

        start_node_name = self.get_start_node_name()
        question_node = Node(
            id=self.start_node_id,
            state=self.STATE.FINISH,
            question=rethink_question,
            answer=str([n.query for n in rewrite_question_list]),
            title=start_node_name,
            logs=None,
        )
        self.sub_query_node.append(question_node)

        for idx, item in enumerate(rewrite_question_list):
            cur_node = Node(
                id=len(self.sub_query_node),
                state=self.STATE.WAITING,
                question=item.query,
                answer=None,
                logs=None,
                title=self.get_sub_question_name(idx + 1),
            )
            self.sub_query_node.append(cur_node)

        # Generate edges between nodes
        for idx, item in enumerate(self.sub_query_node, start=1):
            if item.id == 0:
                continue
            if idx == len(self.sub_query_node):
                pipeline.edges.append(Edge(_from=item.id, to=0))
                break
            else:
                pipeline.edges.append(
                    Edge(_from=item.id, to=self.sub_query_node[idx].id)
                )
        pipeline.nodes = self.sub_query_node

        request = ReportPipelineRequest(task_id=self.task_id, pipeline=pipeline)
        if self.report_log:
            self.client.reasoner_dialog_report_pipeline_post(
                report_pipeline_request=request
            )
        else:
            logger.info(request)
        self.last_sub_question_size = len(rewrite_question_list)
        self.create_pipeline_times += 1

    def report_final_answer(self, query, answer, state):
        node = self.sub_query_node[0]
        node._state = state
        node._question = query
        node._answer = answer
        request = ReportPipelineRequest(task_id=self.task_id, node=node)
        if self.report_log:
            self.client.reasoner_dialog_report_node_post(
                report_pipeline_request=request
            )
        else:
            logger.info(request)

    def report_node(self, req_id, index, state, node_plan: LFPlan, kg_graph: KgGraph):
        """
        Report a single node in the pipeline.

        Args:
            req_id (str): Request ID.
            index (int): Index of the node.
            state (STATE): State of the node.
            node_plan (LFPlan): Logical form plan for the node.
            kg_graph (KgGraph): Knowledge graph associated with the node.
        """
        sub_logic_nodes_str = "\n".join([str(ln) for ln in node_plan.lf_nodes])
        # 为产品展示隐藏冗余信息
        sub_logic_nodes_str = re.sub(
            r"(\s,sub_query=[^)]+|get\([^)]+\))", "", sub_logic_nodes_str
        ).strip()
        context = [
            "## SPO Retriever",
            "#### logic_form expression: ",
            f"```java\n{sub_logic_nodes_str}\n```",
        ]
        sub_answer = None
        if node_plan.res is not None:
            sub_answer, cur_content, sub_graph = self._convert_lf_res_to_report_format(
                req_id=req_id,
                index=index,
                state=state,
                res=node_plan.res,
                kg_graph=kg_graph,
            )
            context += cur_content
        else:
            sub_graph = None

        logs = self.format_logs(context)
        report_node_id = self.start_node_id + index if index != 0 else 0
        node = self.sub_query_node[report_node_id]
        node._state = state
        node._question = node_plan.query
        node._answer = sub_answer
        node._logs = logs
        if sub_graph is not None:
            node._subgraph = [sub_graph]
        request = ReportPipelineRequest(task_id=self.task_id, node=node)
        if self.report_log:
            self.client.reasoner_dialog_report_node_post(
                report_pipeline_request=request
            )
        else:
            logger.info(request)

    def _convert_lf_res_to_report_format(
        self, req_id, index, state, res: SubQueryResult, kg_graph: KgGraph
    ):
        """
        Convert logical form result to a report format.

        Args:
            req_id (str): Request ID.
            index (int): Index of the node.
            state (STATE): State of the node.
            res (SubQueryResult): Result of the logical form query.
            kg_graph (KgGraph): Knowledge graph associated with the node.

        Returns:
            tuple: Sub-answer, context content, and sub-graph.
        """
        spo_retrieved = res.spo_retrieved
        context = []
        sub_answer = None
        if len(spo_retrieved) > 0:
            spo_answer_path = json.dumps(
                kg_graph.to_spo_path(spo_retrieved, self.language),
                ensure_ascii=False,
                indent=4,
            )
            spo_answer_path = f"```json\n{spo_answer_path}\n```"
            graph_id = f"{req_id}_{index}"
            graph_div = f"<div class='{graph_id}'></div>\n\n"
            sub_graph = self._convert_spo_to_graph(graph_id, spo_retrieved)
            context.append(graph_div)
            context.append(f"#### Triplet Retrieved:")
            context.append(spo_answer_path)
        else:
            context.append(f"#### Triplet Retrieved:")
            context.append("No triplets were retrieved.")
            sub_graph = None

        doc_retrieved = res.doc_retrieved
        context += self._update_sub_question_recall_docs(doc_retrieved)
        if state == ReporterIntermediateProcessTool.STATE.FINISH:
            context.append(f"#### answer based by {res.match_type}:")
            context.append(f"{res.sub_answer}")
            sub_answer = res.sub_answer
        return sub_answer, context, sub_graph

    def _convert_spo_to_graph(self, graph_id, spo_retrieved):
        """
        Convert SPO triples to a graph representation.

        Args:
            spo_retrieved (list): List of SPO triples.

        Returns:
            SubGraph: Graph representation of the SPO triples.
        """
        nodes = {}
        edges = []
        for spo in spo_retrieved:

            def _get_node(entity: EntityData):
                node = DataNode(
                    id=entity.to_show_id(self.language),
                    name=entity.get_short_name(),
                    label=entity.type_zh if self.language == "zh" else entity.type,
                    properties=entity.prop.get_properties_map() if entity.prop else {},
                )
                return node

            start_node = _get_node(spo.from_entity)
            end_node = _get_node(spo.end_entity)
            if start_node.id not in nodes:
                nodes[start_node.id] = start_node
            if end_node.id not in nodes:
                nodes[end_node.id] = end_node
            spo_id = spo.to_show_id(self.language)
            data_spo = DataEdge(
                id=spo_id,
                _from=start_node.id,
                from_type=start_node.label,
                to=end_node.id,
                to_type=end_node.label,
                properties=spo.prop.get_properties_map() if spo.prop else {},
                label=spo.type_zh if self.language == "zh" else spo.type,
            )
            edges.append(data_spo)
        sub_graph = SubGraph(
            class_name=graph_id, result_nodes=list(nodes.values()), result_edges=edges
        )
        return sub_graph

    def _update_sub_question_recall_docs(self, docs):
        """
        Update the context with retrieved documents for sub-questions.

        Args:
            docs (list): List of retrieved documents.

        Returns:
            list: Updated context content.
        """
        if docs is None or len(docs) == 0:
            return []
        doc_content = [f"## Chunk Retriever"]
        doc_content.extend(["|id|content|", "|-|-|"])
        for i, d in enumerate(docs, start=1):
            _d = d.replace("\n", "<br>")
            doc_content.append(f"|{i}|{_d}|")
        return doc_content

    def format_logs(self, logs):
        """
        Format logs into a string.

        Args:
            logs (list or str): Logs to be formatted.

        Returns:
            str: Formatted log content.
        """
        if not logs:
            return None
        content = ""
        if isinstance(logs, str):
            try:
                logs = json.loads(logs)
            except:
                logs = eval(logs)
        for idx, item in enumerate(logs, start=1):
            content += f"{item}\n"
        return content
