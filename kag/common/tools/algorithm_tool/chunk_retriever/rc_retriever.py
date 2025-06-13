import logging
from typing import Optional


from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF
from kag.common.config import LogicFormConfiguration
from kag.common.text_sim_by_vector import TextSimilarity
from kag.interface import VectorizeModelABC, RetrieverABC, RetrieverOutput
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.interface.solver.reporter_abc import ReporterABC


from kag.common.tools.algorithm_tool.chunk_retriever.vector_chunk_retriever import (
    VectorChunkRetriever,
)
from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
from kag.common.tools.search_api.search_api_abc import SearchApiABC

logger = logging.getLogger()


@RetrieverABC.register("rc_open_spg")
class RCRetrieverOnOpenSPG(RetrieverABC):
    def __init__(
        self,
        top_k=10,
        vector_chunk_retriever: VectorChunkRetriever = None,
        vectorize_model: VectorizeModelABC = None,
        search_api: SearchApiABC = None,
        graph_api: GraphApiABC = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.name = kwargs.get("name", "kg_rc")
        self.top_k = top_k
        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            KAG_CONFIG.all_config["vectorize_model"]
        )
        self.text_similarity = TextSimilarity(vectorize_model)

        self.search_api = search_api or SearchApiABC.from_config(
            {"type": "openspg_search_api"}
        )
        self.graph_api = graph_api or GraphApiABC.from_config(
            {"type": "openspg_graph_api"}
        )

        self.vector_chunk_retriever = vector_chunk_retriever or VectorChunkRetriever(
            vectorize_model=self.vectorize_model, search_api=self.search_api
        )

        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
                }
            )
        )

    def invoke(self, task, **kwargs) -> RetrieverOutput:
        segment_name = kwargs.get("segment_name", "thinker")
        component_name = self.name
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        query = task.arguments.get("rewrite_query", task.arguments["query"])

        if reporter:
            reporter.add_report_line(
                segment_name,
                f"begin_sub_kag_retriever_{query}_{component_name}",
                query,
                "INIT",
                component_name=component_name,
            )

        output = self.vector_chunk_retriever.invoke(task=task, **kwargs)
        if reporter:
            reporter.add_report_line(
                segment_name,
                f"begin_sub_kag_retriever_{query}_{component_name}",
                "",
                "FINISH",
                component_name=component_name,
                chunk_num=min(len(output.chunks), self.top_k),
                desc="retrieved_doc_digest",
            )

        return output

    def schema(self):
        return {
            "name": "kg_rc_retriever",
            "description": "Retrieve chunk data",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for context retrieval",
                    }
                },
                "required": ["query"],
            },
        }
