import re
from typing import Dict, List

from kag.common.conf import KAG_PROJECT_CONF
from kag.solver.execute.op_executor.op_deduce.module.choice import ChoiceOp
from kag.solver.execute.op_executor.op_deduce.module.entailment import EntailmentOp
from kag.solver.execute.op_executor.op_deduce.module.judgement import JudgementOp
from kag.solver.execute.op_executor.op_deduce.module.multi_choice import MultiChoiceOp
from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.interface.solver.base_model import LogicNode, LFPlan
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import (
    DeduceNode
)


class DeduceExecutor(OpExecutor):
    def __init__(self, schema: SchemaUtils, **kwargs):
        super().__init__(schema, **kwargs)
        self.KAG_PROJECT_ID = (KAG_PROJECT_CONF.project_id,)

    def _deduce_call(
        self,
        nl_query: str,
        lf_plan: LFPlan,
        req_id: str,
        kg_graph: KgGraph,
        process_info: dict,
        history: List[LFPlan],
        param: dict,
    ) -> Dict:
        op_mapping = {
            "choice": ChoiceOp(
                self.schema,
                KAG_PROJECT_ID=self.KAG_PROJECT_ID,
                **param
            ),
            "multiChoice": MultiChoiceOp(
                self.schema,
                KAG_PROJECT_ID=self.KAG_PROJECT_ID,
                **param
            ),
            "entailment": EntailmentOp(
                self.schema,
                KAG_PROJECT_ID=self.KAG_PROJECT_ID,
                **param
            ),
            "judgement": JudgementOp(
                self.schema,
                KAG_PROJECT_ID=self.KAG_PROJECT_ID,
                **param
            ),
        }
        node: DeduceNode = lf_plan.lf_node
        kg_graph.alias_set.append(node.alias_name)
        content = node.content
        try:
            content_l = re.findall('`(.*?)`', content)
        except Exception as e:
            # breakpoint()
            content_l = []
        contents = []
        for c in content_l:
            values = kg_graph.get_answered_alias(c)
            if values is not None:
                c = str(values)
            elif values == "":
                continue
            contents.append(c)
        contents = '\n'.join(contents)
        process_info[node.sub_query]["input_contents"] = contents
        target = node.target
        result = []
        final_if_answered = False
        for op in node.ops:
            res = op_mapping[op].executor(target if target else nl_query, lf_plan, req_id, kg_graph, process_info, history,
                                          param)
            if_answered = res["if_answered"]
            answer = res["answer"]
            result.append(answer)
            final_if_answered = if_answered or final_if_answered
        process_info[node.sub_query]["kg_answer"] += f"\n{';'.join(result)}"
        process_info[node.sub_query]["if_answered"] = final_if_answered
        if final_if_answered:
            kg_graph.add_answered_alias(node.alias_name, ";".join(process_info[node.sub_query]["kg_answer"]))

        lf_plan.res.sub_answer = process_info[lf_plan.query]["kg_answer"]
        lf_plan.res.if_answered = final_if_answered
        lf_plan.res.match_type = lf_plan.sub_query_type
        return process_info[node.sub_query]

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(
            logic_node, (DeduceNode)
        )

    def executor(self, nl_query: str, lf_plan: LFPlan, req_id: str, kg_graph: KgGraph, process_info: dict,
                 history: List[LFPlan], param: dict) -> Dict:
        return self._deduce_call(
            nl_query, lf_plan, req_id, kg_graph, process_info, history, param
        )