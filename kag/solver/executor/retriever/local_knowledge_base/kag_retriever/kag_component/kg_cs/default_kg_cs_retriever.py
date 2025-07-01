from typing import List

from kag.common.config import get_default_chat_llm_config
from kag.interface import LLMClient, Task
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.model.one_hop_graph import RetrievedData
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
from kag.common.tools.algorithm_tool.graph_retriever.entity_linking import EntityLinking
from kag.common.tools.algorithm_tool.graph_retriever.path_select.path_select import (
    PathSelect,
)


@FlowComponent.register("kg_cs_open_spg_legacy")
class KgConstrainRetrieverWithOpenSPG(KagLogicalFormComponent):
    def __init__(
        self,
        path_select: PathSelect = None,
        entity_linking=None,
        llm: LLMClient = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.name = kwargs.get("name", "kg_cs")
        self.llm = llm or LLMClient.from_config(get_default_chat_llm_config())
        self.path_select = path_select or PathSelect.from_config(
            {"type": "exact_one_hop_select"}
        )
        if isinstance(entity_linking, dict):
            entity_linking = EntityLinking.from_config(entity_linking)
        self.entity_linking = entity_linking or EntityLinking.from_config(
            {
                "type": "default_entity_linking",
                "recognition_threshold": 0.9,
                "exclude_types": ["Chunk"],
            }
        )
        self.template = KgRetrieverTemplate(
            path_select=self.path_select,
            entity_linking=self.entity_linking,
            llm_module=self.llm,
        )

    def invoke(
        self,
        cur_task: FlowComponentTask,
        executor_task: Task,
        processed_logical_nodes: List[LogicNode],
        **kwargs
    ) -> List[RetrievedData]:
        query = executor_task.arguments.get(
            "rewrite_query", executor_task.arguments["query"]
        )
        return [
            self.template.invoke(
                query=query,
                logic_nodes=[cur_task.logical_node],
                graph_data=cur_task.graph_data,
                is_exact_match=True,
                name=self.name,
                **kwargs
            )
        ]
