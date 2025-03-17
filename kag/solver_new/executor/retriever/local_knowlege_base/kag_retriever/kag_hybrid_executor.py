from typing import List, Any


from kag.interface import ExecutorABC, ExecutorResponse
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_flow import KAGFlow
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_types.logic_node.logic_node import \
    LogicNode


class KAGRetrievedResponse(ExecutorResponse):
    """Response object containing retrieved data from knowledge graph processing.

    Attributes:
        sub_retrieved_set (List[SubRetrievedData]): List of processed sub-question results
        retrieved_task (str): Original task description
    """

    def __init__(self):
        super().__init__()
        self.sub_retrieved_set = []  # Collection of processed sub-question results
        self.retrieved_task = ""  # Original task description
        self.graph_data = None
        self.chunk_datas = []
    def __str__(self):
        return f"task: f{self.retrieved_task}" + "\n".join(
            [str(item) for item in self.sub_retrieved_set]
        )

    __repr__=__str__

    def to_string(self) -> str:
        """Convert response to human-readable string format

        Returns:
            str: Formatted string containing task description and sub-question results

        Note:
            Contains formatting error: "task: f{self.retrieved_task}"
            should be corrected to "task: {self.retrieved_task}"
        """
        return str(self)


@ExecutorABC.register("kag_hybrid_executor")
class KagHybridExecutor(ExecutorABC):
    """Hybrid knowledge graph retrieval executor combining multiple strategies.

    Combines entity linking, path selection, and text chunk retrieval using
    knowledge graph and LLM capabilities to answer complex queries.
    """

    def __init__(
        self,
        flow,
        lf_rewriter= None,
    ):
        super().__init__()
        self.lf_rewriter = lf_rewriter
        self.flow_str = flow

    @property
    def output_types(self):
        """Output type specification for executor responses"""
        return KAGRetrievedResponse

    def invoke(
        self, query: str, task: Any, context: dict, **kwargs
    ):
        """Execute hybrid knowledge graph retrieval process

        Args:
            query (str): User input question
            task: Task configuration object
            context (dict): Context information for retrieval
            **kwargs: Additional parameters

        Returns:
            KAGRetrievedResponse: Aggregated retrieval results

        Steps:
            1. Initialize response container
            2. Convert query to logical form
            3. Initialize knowledge graph container
            4. Process each logical node
            5. Retrieve text chunks
            6. Generate summaries
            7. Save intermediate results
            8. Store final results
        """
        # 1. Initialize response container
        kag_response = self._initialize_response(task)
        # 2. Convert query to logical form
        task_query = task.arguments['query']
        logic_nodes = self._convert_to_logical_form(task_query, task)

        flow: KAGFlow = KAGFlow(nl_query=task_query, lf_nodes=logic_nodes, flow_str=self.flow_str)

        graph_data, retrieved_datas = flow.execute()
        kag_response.graph_data = graph_data
        kag_response.chunk_datas = retrieved_datas
        for lf_node in logic_nodes:
            kag_response.sub_retrieved_set.append(lf_node.get_fl_node_result())

        # 8. Final storage
        self._store_results(task, kag_response)

    def _initialize_response(self, task) -> KAGRetrievedResponse:
        """Create and initialize response container

        Args:
            task: Task configuration object containing description

        Returns:
            KAGRetrievedResponse: Initialized response object
        """
        response = KAGRetrievedResponse()
        response.retrieved_task = str(task)
        return response

    def _convert_to_logical_form(self, query: str, task) -> List[LogicNode]:
        """Convert task description to logical nodes

        Args:
            query (str): User input query
            task: Task configuration object

        Returns:
            List[GetSPONode]: Logical nodes derived from task description
        """
        # TODO 在拆解的时候应该需要本任务依赖的任务，此处需要从context中获取，还需要改下代码
        dep_tasks = task.parents
        context = []
        for dep_task in dep_tasks:
            if not dep_task.result:
                continue
            context.append(dep_task.result)
        return self._trans_query_to_logic_form(query, str(context))

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
