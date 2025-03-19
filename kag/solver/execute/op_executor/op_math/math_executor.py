from typing import Union, Dict, List

from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.interface.solver.base_model import LogicNode, LFPlan
from kag.solver.execute.op_executor.op_math.coder_math.coder_math_op import CoderMathOp
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import MathNode


class MathExecutor(OpExecutor):
    def __init__(self, schema: SchemaUtils, **kwargs):
        super().__init__(schema, **kwargs)
        self.op_mapping = {
            'math': CoderMathOp(self.schema, **kwargs),
        }

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, MathNode)

    def executor(self, nl_query: str, lf_plan: LFPlan, req_id: str, kg_graph: KgGraph, process_info: dict,
                 history: List[LFPlan], param: dict) -> Dict:
        math_node: MathNode = lf_plan.lf_node
        kg_graph.alias_set.append(math_node.alias_name)
        result = self.op_mapping[lf_plan.lf_node.operator].executor(nl_query, lf_plan, req_id, kg_graph, process_info, history,
                                                            param)
        if_answered = result['if_answered']
        answer = result['answer']
        if if_answered:
            kg_graph.add_answered_alias(math_node.alias_name, answer)
        process_info[lf_plan.lf_node.sub_query]["kg_answer"] = answer
        process_info[lf_plan.lf_node.sub_query]["if_answered"] = if_answered
        lf_plan.res.sub_answer = answer
        lf_plan.res.if_answered = if_answered

        return process_info
