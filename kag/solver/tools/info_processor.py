import json
import logging
from enum import Enum

from knext.common.rest import ApiClient, Configuration
from knext.reasoner.rest.models.ca_pipeline import CaPipeline
from knext.reasoner.rest.models.edge import Edge
from knext.reasoner.rest.models.node import Node
from knext.reasoner.rest.models.report_pipeline_request import ReportPipelineRequest
from knext.reasoner.rest.reasoner_api import ReasonerApi

logger = logging.getLogger(__name__)
class ReporterIntermediateProcessTool:
    class STATE(str, Enum):
        WAITING = "WAITING"
        RUNNING = "RUNNING"
        FINISH = "FINISH"
        ERROR = "ERROR"

    ROOT_ID = 0

    def __init__(self, report_log=False, task_id=None, project_id=None, host_addr=None):
        self.report_log = report_log
        self.task_id = task_id
        self.project_id = project_id
        self.client: ReasonerApi = ReasonerApi(
            api_client=ApiClient(configuration=Configuration(host=host_addr)))

    def report_pipeline(self, question, rewrite_question_list=[]):
        # print(question)
        for idx, item in enumerate(rewrite_question_list, start=2):
            item.id = idx
            # print(item)

        pipeline = CaPipeline()
        pipeline.nodes = []
        pipeline.edges = []
        pipeline.nodes.append(Node(id=self.ROOT_ID, state=self.STATE.WAITING, question=question.question, answer=None, logs=None))
        dep_question_list = []
        for item in rewrite_question_list:
            pipeline.nodes.append(Node(id=item.id, state=self.STATE.WAITING, question=item.question, answer=None, logs=None))
            if item.dependencies:
                for dep_item in item.dependencies:
                    pipeline.edges.append(Edge(_from=dep_item.id, to=item.id))
                    dep_question_list.append(dep_item)
        for item in rewrite_question_list:
            if item not in dep_question_list:
                pipeline.edges.append(Edge(_from=item.id, to=self.ROOT_ID))
        to_list = []
        for edge in pipeline.edges:
            to_list.append(edge.to)
        first_nodes = []
        for node in pipeline.nodes:
            if node.id not in to_list:
                first_nodes.append(node.id)
        # str([n.question for n in pipeline.nodes if n.id != self.ROOT_ID])
        pipeline.nodes.insert(0, Node(id=1, state=self.STATE.FINISH, question=question.question, answer=str([n.question for n in pipeline.nodes if n.id != self.ROOT_ID]), logs=None))
        for n in first_nodes:
            pipeline.edges.insert(0, Edge(_from=1, to=n))
        request = ReportPipelineRequest(task_id=self.task_id, pipeline=pipeline)
        if self.report_log:
            self.client.reasoner_dialog_report_pipeline_post(report_pipeline_request=request)
        else:
            logger.info(request)

    def report_node(self, question, answer, state):
        logs = self.format_logs(question.context)
        if not question.id:
            question.id = self.ROOT_ID
        node = Node(id=(question.id+1 if question.id != 0 else 0), state=state, question=question.question, answer=answer,
        logs=logs)
        request = ReportPipelineRequest(task_id=self.task_id, node=node)
        if self.report_log:
            self.client.reasoner_dialog_report_node_post(report_pipeline_request=request)
        else:
            logger.info(request)

    def format_logs(self, logs):
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
