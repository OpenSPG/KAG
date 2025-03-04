from typing import Dict

from kag.common.conf import KAG_PROJECT_CONF
from kag.solver.execute.op_executor.op_deduce.module.choice import ChoiceOp
from kag.solver.execute.op_executor.op_deduce.module.entailment import EntailmentOp
from kag.solver.execute.op_executor.op_deduce.module.judgement import JudgementOp
from kag.solver.execute.op_executor.op_deduce.module.multi_choice import MultiChoiceOp
from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.interface.solver.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import (
    DeduceNode,
    VerifyNode,
    FilterNode,
    ExtractorNode,
)


class DeduceExecutor(OpExecutor):
    def __init__(self, schema: SchemaUtils, **kwargs):
        super().__init__(schema, **kwargs)
        self.KAG_PROJECT_ID = (KAG_PROJECT_CONF.project_id,)

    def _deduce_call(
        self,
        nl_query: str,
        node: DeduceNode,
        req_id: str,
        kg_graph: KgGraph,
        process_info: dict,
        param: dict,
    ) -> Dict:
        op_mapping = {
            "choice": ChoiceOp(
                self.schema,
                KAG_PROJECT_ID=self.KAG_PROJECT_ID,
            ),
            "multiChoice": MultiChoiceOp(
                self.schema,
                KAG_PROJECT_ID=self.KAG_PROJECT_ID,
            ),
            "entailment": EntailmentOp(
                self.schema,
                KAG_PROJECT_ID=self.KAG_PROJECT_ID,
            ),
            "judgement": JudgementOp(
                self.schema,
                KAG_PROJECT_ID=self.KAG_PROJECT_ID,
            ),
        }
        result = []
        for op in node.deduce_ops:
            res = op_mapping[op].executor(
                nl_query, node, req_id, kg_graph, process_info, param
            )
            if_answered = res["if_answered"]
            answer = res["answer"]
            if if_answered:
                result.append(answer)
        process_info[node.sub_query]["kg_answer"] += f"\n{';'.join(result)}"
        return process_info[node.sub_query]

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(
            logic_node, (DeduceNode, FilterNode, VerifyNode, ExtractorNode)
        )

    def executor(
        self,
        nl_query: str,
        logic_node: LogicNode,
        req_id: str,
        kg_graph: KgGraph,
        process_info: dict,
        param: dict,
    ) -> Dict:
        if isinstance(logic_node, DeduceNode):
            return self._deduce_call(
                nl_query, logic_node, req_id, kg_graph, process_info, param
            )
        raise NotImplementedError(f"{logic_node}")
