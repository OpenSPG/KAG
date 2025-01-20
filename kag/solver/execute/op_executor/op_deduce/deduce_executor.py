import re
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
        content = node.content
        nodes_alias = kg_graph.nodes_alias
        query_graph_alias = []
        for _, spo in kg_graph.query_graph.items():
            query_graph_alias.append(spo["s"])
            query_graph_alias.append(spo["o"])
            query_graph_alias.append(spo["p"])
        query_graph_alias = list(set(query_graph_alias))
        try:
            content_l = re.findall('`(.*?)`', content)
        except Exception as e:
            # breakpoint()
            content_l = []
        contents = []
        for c in content_l:
            if c in query_graph_alias:
                values = kg_graph.get_entity_by_alias(c)
                if values is not None:
                    c = str(values)
                else:
                    continue
            contents.append(c)
        contents = '\n'.join(contents)
        process_info[node.sub_query]["input_contents"] = contents
        target = node.target
        result = []
        final_if_answered = False
        for op in node.ops:
            res = op_mapping[op].executor(
                target if target else nl_query, node, req_id, kg_graph, process_info, param
            )
            if_answered = res["if_answered"]
            answer = res["answer"]
            result.append(answer)
            final_if_answered = if_answered or final_if_answered
        process_info[node.sub_query]["kg_answer"] += f"\n{';'.join(result)}"
        process_info[node.sub_query]["if_answered"] = final_if_answered
        if final_if_answered:
            kg_graph.add_mock_entity(node.alias_name, ";".join(process_info[node.sub_query]["kg_answer"]))
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
