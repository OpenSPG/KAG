import logging
import math
import time
from typing import List, Dict, Optional

from kag.interface.solver.reporter_abc import ReporterABC
from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.common.config import get_default_chat_llm_config
from kag.common.text_sim_by_vector import TextSimilarity
from kag.interface import Task, PromptABC, LLMClient, VectorizeModelABC
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.model.one_hop_graph import RetrievedData, KgGraph
from kag.interface.solver.planner_abc import format_task_dep_context
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponent,
    FlowComponentTask,
)
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.utils import (
    get_chunks,
    generate_step_query,
)
from kag.solver.utils import init_prompt_with_fallback
from kag.common.tools.algorithm_tool.chunk_retriever.vector_chunk_retriever import (
    VectorChunkRetriever,
)
from kag.common.tools.search_api.search_api_abc import SearchApiABC

logger = logging.getLogger()


def weightd_merge(
    chunk1: Dict[str, float], chunk2: Dict[str, float], alpha: float = 0.5
):
    def min_max_normalize(chunks):
        if len(chunks) == 0:
            return {}
        scores = chunks.values()
        max_score = max(scores)
        min_score = min(scores)
        ret_docs = {}
        for doc_id, score in chunks.items():
            if math.isclose(max_score, min_score, rel_tol=1e-9):
                score = 1
            else:
                score = (score - min_score) / (max_score - min_score)
            ret_docs[doc_id] = score
        return ret_docs

    chunk1 = min_max_normalize(chunk1)
    chunk2 = min_max_normalize(chunk2)

    merged = {}
    for doc_id, score in chunk1.items():
        if doc_id in merged:
            merged_score = merged[doc_id]
            merged_score += score * alpha
            merged[doc_id] = merged_score
        else:
            merged[doc_id] = score * alpha

    for doc_id, score in chunk2.items():
        if doc_id in merged:
            merged_score = merged[doc_id]
            merged_score += score * (1 - alpha)
            merged[doc_id] = merged_score
        else:
            merged[doc_id] = score * (1 - alpha)

    return merged


@FlowComponent.register("kg_merger")
class KagMerger(FlowComponent):
    def __init__(
        self,
        top_k,
        llm_module: LLMClient = None,
        summary_prompt: PromptABC = None,
        vectorize_model: VectorizeModelABC = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.name = "kag_merger"
        self.top_k = top_k
        self.llm_module = llm_module or LLMClient.from_config(
            get_default_chat_llm_config()
        )
        self.summary_prompt = summary_prompt or init_prompt_with_fallback(
            "thought_then_answer", kag_project_config.biz_scene
        )

        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            kag_config.all_config["vectorize_model"]
        )
        self.text_similarity = TextSimilarity(vectorize_model)

    def invoke(
        self,
        cur_task: FlowComponentTask,
        executor_task: Task,
        processed_logical_nodes: List[LogicNode],
        input_components: List[FlowComponentTask],
        **kwargs,
    ) -> List[RetrievedData]:

        component_chunk_scores = []
        chunk_id_map = {}
        for component in input_components:
            chunks = get_chunks(component.result)
            chunk_scores = {}
            for c in chunks:
                chunk_id_map[c.chunk_id] = c
                chunk_scores[c.chunk_id] = c.score
            component_chunk_scores.append(chunk_scores)
        merged_docs = component_chunk_scores[0]
        for i in range(1, len(component_chunk_scores)):
            merged_docs = weightd_merge(
                chunk1=merged_docs, chunk2=component_chunk_scores[i], alpha=0.5
            )
        sorted_scores = sorted(
            merged_docs.items(), key=lambda item: item[1], reverse=True
        )
        merged_chunks = []
        for doc_id, score in sorted_scores:
            c = chunk_id_map[doc_id]
            c.score = score
            merged_chunks.append(c)
        limited_merged_chunks = merged_chunks[: self.top_k]

        cur_task.logical_node.get_fl_node_result().chunks = limited_merged_chunks

        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)

        if reporter:
            reporter.add_report_line(
                kwargs.get("segment_name", "thinker"),
                f"begin_sub_kag_retriever_{cur_task.logical_node.sub_query}_{self.name}",
                "",
                "FINISH",
                component_name=self.name,
                chunk_num=len(limited_merged_chunks),
                desc=(
                    "kag_merger_digest"
                    if len(limited_merged_chunks) > 0
                    else "kag_merger_digest_failed"
                ),
            )
        # summary
        formatted_docs = []
        for doc in limited_merged_chunks:
            formatted_docs.append(f"{doc.content}")
        if len(formatted_docs) == 0:
            selected_rel = list(set(cur_task.graph_data.get_all_spo()))
            formatted_docs = [str(rel) for rel in selected_rel]
        deps_context = format_task_dep_context(executor_task.parents)

        if not cur_task.logical_node.get_fl_node_result().summary:
            summary_query = generate_step_query(
                logical_node=cur_task.logical_node,
                processed_logical_nodes=processed_logical_nodes,
                start_index=len(deps_context),
            )

            summary_response = self.llm_module.invoke(
                {
                    "cur_question": summary_query,
                    "questions": "\n\n".join(deps_context),
                    "docs": "\n\n".join(formatted_docs),
                },
                self.summary_prompt,
                with_json_parse=False,
                with_except=True,
                tag_name=f"begin_summary_{cur_task.logical_node.sub_query}_{self.name}",
                **kwargs,
            )
            cur_task.logical_node.get_fl_node_result().summary = summary_response
        return limited_merged_chunks + [cur_task.graph_data]
