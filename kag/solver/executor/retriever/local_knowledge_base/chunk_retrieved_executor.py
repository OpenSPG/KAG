import logging
import time
from typing import Any, Optional

from kag.interface import ExecutorABC, RetrieverABC
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
    def __init__(self, top_k, retriever: RetrieverABC, **kwargs):
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
        retrieved_result = self.retriever.invoke(task, context=context, **kwargs)

        # Log the retrieved results
        logger.debug(f"Retrieved results: {retrieved_result}")

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
            f"{len(retrieved_result.chunks)}",
            "FINISH",
        )

        # Log the end of the retrieval process and calculate the duration
        end_time = time.time()  # End time logging
        logger.info(
            f"Finished retrieval process for query: {task_query}. Duration: {end_time - start_time} bytes"
        )
        task.update_result(retrieved_result)

    def schema(self) -> dict:
        """Function schema definition for OpenAI Function Calling

        Returns:
            dict: Schema definition in OpenAI Function format
        """
        return {
            "name": "ChunkRetriever",  # Changed from "Retriever"
            "description": "Retrieve relevant knowledge from the local knowledge base.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query for retrieval.",
                    "optional": False,
                },
            },
        }
