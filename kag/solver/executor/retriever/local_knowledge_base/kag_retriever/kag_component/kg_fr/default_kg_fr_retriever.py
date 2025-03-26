from typing import List

from kag.interface.solver.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponent,
)
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.kg_cs.lf_kg_retriever_template import (
    KgRetrieverTemplate,
)
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.kg_fr.kg_fr_retriever import (
    KGFreeRetrieverABC,
)
from kag.tools.algorithm_tool.graph_retriever.entity_linking import EntityLinking
from kag.tools.algorithm_tool.graph_retriever.path_select.path_select import PathSelect


@FlowComponent.register("kg_fr_open_spg", as_default=True)
class KgFreeRetrieverWithOpenSPG(KGFreeRetrieverABC):
    def __init__(self, path_select: PathSelect = None, entity_linking=None, **kwargs):
        super().__init__(**kwargs)
        self.path_select = path_select or PathSelect.from_config(
            {"type": "fuzzy_one_hop_select"}
        )
        self.entity_linking = entity_linking or EntityLinking.from_config(
            {"type": "default_entity_linking", "recognition_threshold": 0.8}
        )
        self.template = KgRetrieverTemplate(
            path_select=self.path_select, entity_linking=self.entity_linking
        )

    def invoke(self, query: str, logic_nodes: List[LogicNode], **kwargs) -> KgGraph:
        return self.template.invoke(query=query, logic_nodes=logic_nodes, **kwargs)

    def is_break(self):
        return self.break_flag

    def break_judge(self, logic_nodes: List[LogicNode], **kwargs):
        self.break_flag = False
