import logging
import time
from typing import Any, Optional

from kag.interface import ExecutorABC, ToolABC
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_hybrid_executor import (
    KAGRetrievedResponse,
    initialize_response,
    store_results,
)
from kag.interface.solver.model.one_hop_graph import ChunkData

logger = logging.getLogger()


@ExecutorABC.register("chunk_retrieved_executor")
class ChunkRetrievedExecutor(ExecutorABC):
    def __init__(self, top_k, retriever: ToolABC, **kwargs):
        super().__init__(**kwargs)
        self.retriever = retriever
        self.top_k = top_k

    @property
    def output_types(self):
        """Output type specification for executor responses"""
        return KAGRetrievedResponse

    def invoke(self, query: str, task: Any, context: dict, **kwargs):
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        task_query = task.arguments["query"]
        kag_response = initialize_response(task)

        # Log the start of the retrieval process
        logger.info(f"Starting retrieval process for query: {task_query}")
        start_time = time.time()

        self.report_content(
            reporter,
            "thinker",
            f"{task_query}_begin_kag_retriever",
            task_query,
            "FINISH",
            overwrite=False,
        )
        retrieved_result = self.retriever.invoke(query=task_query, top_k=self.top_k)

        # Log the retrieved results
        logger.debug(f"Retrieved results: {retrieved_result}")

        chunk_datas = []
        for k, v in retrieved_result.items():
            chunk_datas.append(
                ChunkData(
                    content=v["content"], title=v["name"], chunk_id=k, score=v["score"]
                )
            )
        kag_response.chunk_datas = chunk_datas
        self.report_content(
            reporter,
            "reference",
            f"{task_query}_kag_retriever_result",
            kag_response,
            "FINISH",
        )

        self.report_content(
            reporter,
            f"{task_query}_begin_kag_retriever",
            f"{task_query}_end_kag_retriever",
            f"{len(chunk_datas)}",
            "FINISH",
        )

        # Log the end of the retrieval process and calculate the duration
        end_time = time.time()  # End time logging
        logger.info(
            f"Finished retrieval process for query: {task_query}. Duration: {end_time - start_time} bytes"
        )
        kag_response.summary = "retrieved by local knowledgebase"
        store_results(task, kag_response)

    def schema(self) -> dict:
        """Function schema definition for OpenAI Function Calling

        Returns:
            dict: Schema definition in OpenAI Function format
        """
        return {
            "name": "Retriever",
            "description": "Retrieve relevant knowledge from the local knowledge base.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query for retrieval.",
                    "optional": False,
                },
            },
        }
