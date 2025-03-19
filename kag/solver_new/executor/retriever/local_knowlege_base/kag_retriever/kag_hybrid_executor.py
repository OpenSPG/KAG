import json
import logging
import uuid

from typing import List, Any, Optional

from kag.interface import ExecutorABC, ExecutorResponse
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.logic.core_modules.common.one_hop_graph import ChunkData
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_component.kag_lf_rewriter import \
    KAGLFRewriter
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_flow import KAGFlow

logger = logging.getLogger()

class KAGRetrievedResponse(ExecutorResponse):
    """Response object containing retrieved data from knowledge graph processing.

    Attributes:
        sub_retrieved_set (List[SubRetrievedData]): List of processed sub-question results
        retrieved_task (str): Original task description
    """

    def __init__(self):
        super().__init__()
        self.task_id = "0"
        self.sub_retrieved_set = []  # Collection of processed sub-question results
        self.retrieved_task = ""  # Original task description
        self.graph_data = None
        self.chunk_datas = []

    def __str__(self):
        return self.to_string()

    __repr__ = __str__

    def to_reference_list(self):
        """
        {
            "id": "1-1",
            "content": "于谦（1398年5月13日－1457年2月16日），字廷益，号节庵，浙江杭州府钱塘县（今杭州市上城区）人。明朝政治家、军事家、民族英雄。",
            "document_id": "53052eb0f40b11ef817442010a8a0006",
            "document_name": "test.txt"
        }"""
        refer_docs = []
        refer_id = 0
        for c in self.chunk_datas:
            if isinstance(c, ChunkData):
                refer_docs.append(
                    {
                        "id": f"chunk:{self.task_id}_{refer_id}",
                        "content": c.content,
                        "document_id": c.chunk_id,
                        "document_name": c.title,
                    }
                )
                refer_id += 1
        if not self.graph_data:
            return refer_docs

        for spo in self.graph_data.get_all_spo():
            refer_docs.append(
                {
                    "id": f"chunk:{self.task_id}_{refer_id}",
                    "content": spo.to_show_id(),
                    "document_id": str(uuid.uuid5(uuid.NAMESPACE_URL, spo.to_show_id())),
                    "document_name": "graph data",
                }
            )
            refer_id += 1
        return refer_docs
    def to_string(self) -> str:
        """Convert response to human-readable string format

        Returns:
            str: Formatted string containing task description and sub-question results

        Note:
            Contains formatting error: "task: f{self.retrieved_task}"
            should be corrected to "task: {self.retrieved_task}"
        """
        refer_docs = self.to_reference_list()
        for doc in refer_docs:
            doc.pop("document_id")
        response_str = {
            "retrieved_task": self.retrieved_task,
            "sub_question": [str(item) for item in self.sub_retrieved_set],
            "reference_docs": refer_docs
        }

        return json.dumps(response_str, ensure_ascii=False)


def _initialize_response(task) -> KAGRetrievedResponse:
    """Create and initialize response container

    Args:
        task: Task configuration object containing description

    Returns:
        KAGRetrievedResponse: Initialized response object
    """
    response = KAGRetrievedResponse()
    response.retrieved_task = str(task)
    response.task_id = task.id
    return response


@ExecutorABC.register("kag_hybrid_executor")
class KagHybridExecutor(ExecutorABC):
    """Hybrid knowledge graph retrieval executor combining multiple strategies.

    Combines entity linking, path selection, and text chunk retrieval using
    knowledge graph and LLM capabilities to answer complex queries.
    """

    def __init__(
            self,
            flow,
            lf_rewriter: KAGLFRewriter,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.lf_rewriter: KAGLFRewriter = lf_rewriter
        self.flow_str = flow

    @property
    def output_types(self):
        """Output type specification for executor responses"""
        return KAGRetrievedResponse

    def report_content(self, reporter, segment, tag_id, content, status):
        if reporter:
            reporter.add_report_line(segment, f"{self.schema().get('name')}\n{tag_id}", content, status)

    def invoke(
            self, query: str, task: Any, context: dict, **kwargs
    ):
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        task_query = task.arguments['query']

        try:

            # 1. Initialize response container
            kag_response = _initialize_response(task)
            # 2. Convert query to logical form
            self.report_content(reporter, "thinker", task_query, "begin running executor", "init")
            logic_nodes = self._convert_to_logical_form(task_query, task)
            logic_nodes_str = "\n".join([str(n) for n in logic_nodes])
            self.report_content(reporter, "thinker", task_query, f"""```
{logic_nodes_str}
```""", "running")

            flow: KAGFlow = KAGFlow(nl_query=task_query, lf_nodes=logic_nodes, flow_str=self.flow_str)

            graph_data, retrieved_datas = flow.execute()
            kag_response.graph_data = graph_data
            kag_response.chunk_datas = retrieved_datas
            self.report_content(reporter, "reference", task_query, kag_response, "finish")
            for lf_node in logic_nodes:
                kag_response.sub_retrieved_set.append(lf_node.get_fl_node_result())

            # 8. Final storage
            self._store_results(task, kag_response)
            self.report_content(reporter, "thinker", task_query, "end executor", "finish")
        except Exception as e:
            logger.warning(f"{self.schema().get('name')} executed failed {e}", exc_info=True)
            self.report_content(reporter, "thinker", task_query, f"{self.schema().get('name')} executed failed {e}", "error")

    def _convert_to_logical_form(self, query: str, task) -> List[LogicNode]:
        """Convert task description to logical nodes

        Args:
            query (str): User input query
            task: Task configuration object

        Returns:
            List[GetSPONode]: Logical nodes derived from task description
        """
        dep_tasks = task.parents
        context = []
        for dep_task in dep_tasks:
            if not dep_task.result:
                continue
            context.append(dep_task.result)
        return self.lf_rewriter.rewrite(query=query, context=context)

    def _store_results(self, task, response: KAGRetrievedResponse):
        """Store final results in task context

        Args:
            task: Task configuration object
            response (KAGRetrievedResponse): Processed results
        """
        task.update_memory("response", response)
        task.update_result(response)

    def schema(self) -> dict:
        """Function schema definition for OpenAI Function Calling

        Returns:
            dict: Schema definition in OpenAI Function format
        """
        return {
            "name": "kag_retriever_executor",
            "description": "Retrieve knowledge graph paths based on query and context to answer questions",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "User input question or query text",
                    }
                },
                "required": ["query"],
            },
        }
