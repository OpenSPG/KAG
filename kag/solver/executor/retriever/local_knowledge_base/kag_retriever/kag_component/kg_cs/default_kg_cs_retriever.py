from typing import List

from kag.common.config import get_default_chat_llm_config
from kag.interface import LLMClient
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.model.one_hop_graph import KgGraph
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponent,
)
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.kg_cs.kg_cs_retriever import (
    KGConstrainRetrieverABC,
)
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.kg_cs.lf_kg_retriever_template import (
    KgRetrieverTemplate,
)
from kag.tools.algorithm_tool.graph_retriever.entity_linking import EntityLinking
from kag.tools.algorithm_tool.graph_retriever.path_select.path_select import PathSelect


@FlowComponent.register("kg_cs_open_spg", as_default=True)
class KgConstrainRetrieverWithOpenSPG(KGConstrainRetrieverABC):
    def __init__(self, path_select: PathSelect = None, entity_linking=None, llm:LLMClient = None,**kwargs):
        super().__init__(**kwargs)
        self.llm = llm or LLMClient.from_config(
            get_default_chat_llm_config()
        )
        self.path_select = path_select or PathSelect.from_config(
            {"type": "exact_one_hop_select"}
        )
        self.entity_linking = entity_linking or EntityLinking.from_config(
            {"type": "default_entity_linking", "recognition_threshold": 0.9, "exclude_types": ["Chunk"]}
        )
        self.template = KgRetrieverTemplate(
            path_select=self.path_select, entity_linking=self.entity_linking, llm_module=self.llm
        )

    def invoke(self, query: str, logic_nodes: List[LogicNode], **kwargs) -> KgGraph:
        return self.template.invoke(
            query=query, logic_nodes=logic_nodes, is_exact_match=True, name=self.name, **kwargs
        )

    def is_break(self):
        return self.break_flag

    def break_judge(self, logic_nodes: List[LogicNode], **kwargs):
        for logic_node in logic_nodes:
            if logic_node.get_fl_node_result().spo:
                continue
            self.break_flag = False
            return
        self.break_flag = True
