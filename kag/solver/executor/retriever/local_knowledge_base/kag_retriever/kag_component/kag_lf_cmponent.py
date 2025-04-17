from typing import List, Optional

from kag.common.parser.logic_node_parser import GetSPONode
from kag.interface import Task
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.model.one_hop_graph import RetrievedData, KgGraph
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponent,
    FlowComponentTask,
)


class KagLogicalFormComponent(FlowComponent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "kag_logical_form_comp"

    def invoke(
        self,
        cur_task: Task,
        logical_node: GetSPONode,
        graph_data: KgGraph,
        processed_logical_nodes: List[LogicNode],
        **kwargs,
    ) -> List[RetrievedData]:
        raise NotImplementedError("invoke not implemented yet.")

    def is_break(self):
        return self.break_flag

    def break_judge(self, cur_task: FlowComponentTask, **kwargs):
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        logical_node = cur_task.logical_node
        if logical_node.get_fl_node_result().spo:
            cur_task.break_flag = True
            if reporter:
                reporter.add_report_line(
                    kwargs.get("segment_name", "thinker"),
                    f"begin_sub_kag_retriever_{logical_node.sub_query}_{self.name}",
                    "retrieved_finish",
                    "FINISH",
                    component_name=self.name,
                )
                reporter.add_report_line(
                    kwargs.get("segment_name", "thinker"),
                    f"end_sub_kag_retriever_{logical_node.sub_query}",
                    logical_node.get_fl_node_result().spo,
                    "FINISH",
                    component_name=self.name,
                )
            return
        cur_task.break_flag = False
        if reporter:
            reporter.add_report_line(
                kwargs.get("segment_name", "thinker"),
                f"begin_sub_kag_retriever_{logical_node.sub_query}_{self.name}",
                "next_finish",
                "FINISH",
                component_name=self.name,
            )
        return
