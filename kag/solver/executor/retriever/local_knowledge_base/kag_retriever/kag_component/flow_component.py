from typing import Optional, List

from kag.common.parser.logic_node_parser import GetSPONode
from kag.common.registry import Registrable
from kag.interface.solver.model.one_hop_graph import RetrievedData, KgGraph


class FlowComponentTask:
    def __init__(self):
        self.result: Optional[List[RetrievedData]] = None
        self.logical_node: Optional[GetSPONode] = None
        self.graph_data: Optional[KgGraph] = None
        self.query = ""
        self.break_flag = False
        self.task_name = ""

    def is_break(self):
        return self.break_flag


class FlowComponent(Registrable):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = kwargs.get("type", "")
        self.break_flag = False

    def invoke(self, **kwargs):
        raise NotImplementedError("invoke not implemented yet.")

    def break_judge(self, cur_task: FlowComponentTask, **kwargs):
        cur_task.break_flag = False
