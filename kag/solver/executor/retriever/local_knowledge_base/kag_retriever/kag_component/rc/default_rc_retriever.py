import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional


from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.common.config import LogicFormConfiguration
from kag.common.text_sim_by_vector import TextSimilarity
from kag.interface import Task, VectorizeModelABC
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.interface.solver.reporter_abc import ReporterABC
from kag.interface.solver.model.one_hop_graph import ChunkData
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponentTask,
    FlowComponent,
)
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.kag_lf_cmponent import (
    KagLogicalFormComponent,
)
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.utils import (
    generate_step_query,
    get_all_docs_by_id,
)

from kag.common.tools.algorithm_tool.chunk_retriever.vector_chunk_retriever import (
    VectorChunkRetriever,
)
from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
from kag.common.tools.search_api.search_api_abc import SearchApiABC

logger = logging.getLogger()


@FlowComponent.register("rc_open_spg_legacy")
class RCRetrieverOnOpenSPG(KagLogicalFormComponent):
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
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.name = kwargs.get("name", "kg_rc")
        self.top_k = top_k
        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            kag_config.all_config["vectorize_model"]
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
                    "KAG_PROJECT_ID": kag_project_config.project_id,
                    "KAG_PROJECT_HOST_ADDR": kag_project_config.host_addr,
                }
            )
        )

    def recall_query(self, query):
        sim_scores_start_time = time.time()
        """Process a single query for similarity scores in parallel."""
        query_sim_scores = self.vector_chunk_retriever.invoke(query, self.top_k * 20)
        logger.info(
            f"`{query}` Similarity scores calculation completed in {time.time() - sim_scores_start_time:.2f} seconds."
        )
        return query_sim_scores

    def invoke(
        self,
        cur_task: FlowComponentTask,
        executor_task: Task,
        processed_logical_nodes: List[LogicNode],
        **kwargs,
    ) -> List[ChunkData]:
        segment_name = kwargs.get("segment_name", "thinker")
        component_name = self.name
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        query = executor_task.arguments.get(
            "rewrite_query", executor_task.arguments["query"]
        )
        logical_node = cur_task.logical_node
        step_sub_query = generate_step_query(
            logical_node=logical_node, processed_logical_nodes=processed_logical_nodes
        )
        dpr_queries = [query, step_sub_query]
        dpr_queries = list(set(dpr_queries))

        if reporter:
            reporter.add_report_line(
                segment_name,
                f"begin_sub_kag_retriever_{cur_task.logical_node.sub_query}_{component_name}",
                cur_task.logical_node.sub_query,
                "INIT",
                component_name=component_name,
            )

        sim_scores = {}
        doc_maps = {}
        with ThreadPoolExecutor() as executor:
            sim_result = list(executor.map(self.recall_query, dpr_queries))
            for query_sim_scores in sim_result:
                for doc_id, node in query_sim_scores.items():
                    doc_maps[doc_id] = node
                    score = node["score"]
                    if doc_id not in sim_scores:
                        sim_scores[doc_id] = score
                    elif score > sim_scores[doc_id]:
                        sim_scores[doc_id] = score
        sorted_scores = sorted(
            sim_scores.items(), key=lambda item: item[1], reverse=True
        )
        matched_chunks = []
        for doc_id, doc_score in sorted_scores:
            matched_chunks.append(
                ChunkData(
                    content=doc_maps[doc_id]["content"].replace("_split_0", ""),
                    title=doc_maps[doc_id]["name"].replace("_split_0", ""),
                    chunk_id=doc_id,
                    score=doc_score,
                    properties=doc_maps[doc_id],
                )
            )
        if reporter:
            reporter.add_report_line(
                segment_name,
                f"begin_sub_kag_retriever_{cur_task.logical_node.sub_query}_{component_name}",
                "",
                "FINISH",
                component_name=component_name,
                chunk_num=min(len(matched_chunks), self.top_k),
                desc="retrieved_doc_digest",
            )

        return matched_chunks

    def is_break(self):
        return self.break_flag

    def break_judge(self, cur_task: FlowComponentTask, **kwargs):
        cur_task.break_flag = False
