import logging
import time
from typing import List, Optional

from kag.common.config import get_default_chat_llm_config
from kag.interface import LLMClient, Task, ToolABC
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.model.one_hop_graph import RetrievedData
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponentTask,
    FlowComponent,
)
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.kag_lf_cmponent import (
    KagLogicalFormComponent,
)

from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.kg_cs.lf_kg_retriever_template import (
    KgRetrieverTemplate,
)
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.utils import (
    generate_step_query,
)

from kag.common.tools.algorithm_tool.chunk_retriever.ppr_chunk_retriever import (
    PprChunkRetriever,
)
from kag.common.tools.algorithm_tool.graph_retriever.entity_linking import EntityLinking
from kag.common.tools.algorithm_tool.graph_retriever.path_select.path_select import (
    PathSelect,
)

logger = logging.getLogger()


@FlowComponent.register("kg_fr_open_spg_legacy")
class KgFreeRetrieverWithOpenSPG(KagLogicalFormComponent):
    def __init__(
        self,
        path_select: PathSelect = None,
        entity_linking=None,
        llm: LLMClient = None,
        ppr_chunk_retriever_tool: ToolABC = None,
        top_k=10,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.name = kwargs.get("name", "kg_fr")
        self.llm = llm or LLMClient.from_config(get_default_chat_llm_config())
        self.path_select = path_select or PathSelect.from_config(
            {"type": "fuzzy_one_hop_select"}
        )
        if isinstance(entity_linking, dict):
            entity_linking = EntityLinking.from_config(entity_linking)
        self.entity_linking = entity_linking or EntityLinking.from_config(
            {
                "type": "default_entity_linking",
                "recognition_threshold": 0.8,
                "exclude_types": ["Chunk"],
            }
        )
        self.template = KgRetrieverTemplate(
            path_select=self.path_select,
            entity_linking=self.entity_linking,
            llm_module=self.llm,
        )
        self.ppr_chunk_retriever_tool = (
            ppr_chunk_retriever_tool
            or PprChunkRetriever.from_config(
                {
                    "type": "ppr_chunk_retriever",
                    "llm_client": get_default_chat_llm_config(),
                }
            )
        )
        self.top_k = top_k
        self.disable_chunk = kwargs.get("disable_chunk", False)

    def invoke(
        self,
        cur_task: FlowComponentTask,
        executor_task: Task,
        processed_logical_nodes: List[LogicNode],
        **kwargs,
    ) -> List[RetrievedData]:
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        query = executor_task.arguments.get(
            "rewrite_query", executor_task.arguments["query"]
        )

        graph_data = self.template.invoke(
            query=query,
            logic_nodes=[cur_task.logical_node],
            graph_data=cur_task.graph_data,
            name=self.name,
            **kwargs,
        )
        entities = []
        selected_rel = []
        if graph_data is not None:
            s_entities = graph_data.get_entity_by_alias_without_attr(
                cur_task.logical_node.s.alias_name
            )
            if s_entities:
                entities.extend(s_entities)
            o_entities = graph_data.get_entity_by_alias_without_attr(
                cur_task.logical_node.o.alias_name
            )
            if o_entities:
                entities.extend(o_entities)
            selected_rel = graph_data.get_all_spo()
            entities = list(set(entities))

        ppr_sub_query = generate_step_query(
            logical_node=cur_task.logical_node,
            processed_logical_nodes=processed_logical_nodes,
        )

        if self.disable_chunk:
            cur_task.logical_node.get_fl_node_result().spo = selected_rel
            cur_task.logical_node.get_fl_node_result().sub_question = ppr_sub_query
            return [graph_data]

        ppr_queries = [query, ppr_sub_query]
        ppr_queries = list(set(ppr_queries))
        start_time = time.time()
        chunks, match_spo = self.ppr_chunk_retriever_tool.invoke(
            queries=ppr_queries,
            start_entities=entities,
            top_k=self.top_k,
        )

        logger.info(
            f"`{query}`  Retrieved chunks num: {len(chunks)} cost={time.time() - start_time}"
        )
        cur_task.logical_node.get_fl_node_result().spo = match_spo + selected_rel
        cur_task.logical_node.get_fl_node_result().chunks = chunks
        cur_task.logical_node.get_fl_node_result().sub_question = ppr_sub_query
        if reporter:
            reporter.add_report_line(
                kwargs.get("segment_name", "thinker"),
                f"begin_sub_kag_retriever_{cur_task.logical_node.sub_query}_{self.name}",
                "",
                "FINISH",
                component_name=self.name,
                chunk_num=len(chunks),
                nodes_num=len(entities),
                edges_num=len(selected_rel),
                desc="retrieved_info_digest",
            )
        return [graph_data] + chunks
