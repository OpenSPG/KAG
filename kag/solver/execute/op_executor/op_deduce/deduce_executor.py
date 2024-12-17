from typing import Union

from kag.solver.execute.op_executor.op_deduce.module.choice import ChoiceOp
from kag.solver.execute.op_executor.op_deduce.module.entailment import EntailmentOp
from kag.solver.execute.op_executor.op_deduce.module.judgement import JudgementOp
from kag.solver.execute.op_executor.op_deduce.module.multi_choice import MultiChoiceOp
from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.solver.logic.core_modules.common.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import DeduceNode, VerifyNode, FilterNode, ExtractorNode


class DeduceExecutor(OpExecutor):
    def __init__(
        self,
        kg_graph: KgGraph,
        schema: SchemaUtils,
        debug_info: dict,
        **kwargs
    ):
        super().__init__(kg_graph, schema, debug_info, **kwargs)
        self.KAG_PROJECT_ID = kwargs.get("KAG_PROJECT_ID")

    def _deduce_call(self, node: DeduceNode, req_id: str, param: dict) -> list:
        op_mapping = {
            "choice": ChoiceOp(
                self.kg_graph,
                self.schema,
                self.debug_info,
                KAG_PROJECT_ID=self.KAG_PROJECT_ID,
            ),
            "multiChoice": MultiChoiceOp(
                self.kg_graph,
                self.schema,
                self.debug_info,
                KAG_PROJECT_ID=self.KAG_PROJECT_ID,
            ),
            "entailment": EntailmentOp(
                self.kg_graph,
                self.schema,
                self.debug_info,
                KAG_PROJECT_ID=self.KAG_PROJECT_ID,
            ),
            "judgement": JudgementOp(
                self.kg_graph,
                self.schema,
                self.debug_info,
                KAG_PROJECT_ID=self.KAG_PROJECT_ID,
            ),
        }
        result = []
        for op in node.deduce_ops:
            if_answered, answer = op_mapping[op].executor(node, req_id, param)
            if if_answered:
                result.append(answer)
        return result

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(
            logic_node, (DeduceNode, FilterNode, VerifyNode, ExtractorNode)
        )

    def executor(
        self, nl_query: str, logic_node: LogicNode, req_id: str, param: dict
    ) -> Union[KgGraph, list]:
        if isinstance(logic_node, DeduceNode):
            return self._deduce_call(logic_node, req_id, param)
        raise NotImplementedError(f"{logic_node}")
