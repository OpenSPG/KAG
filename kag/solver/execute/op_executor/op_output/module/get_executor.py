from typing import Dict

from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.interface.solver.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import (
    KgGraph,
    EntityData,
    RelationData,
)
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import GetNode


class GetExecutor(OpExecutor):
    def __init__(self, schema: SchemaUtils, **kwargs):
        super().__init__(schema, **kwargs)

    def executor(
        self,
        nl_query: str,
        logic_node: LogicNode,
        req_id: str,
        kg_graph: KgGraph,
        process_info: dict,
        param: dict,
    ) -> Dict:
        kg_qa_result = []
        if not isinstance(logic_node, GetNode):
            return process_info[logic_node.sub_query]

        n = logic_node
        s_data_set = kg_graph.get_entity_by_alias(n.alias_name)
        if s_data_set is None:
            return process_info[logic_node.sub_query]

        for s_data in s_data_set:
            if isinstance(s_data, EntityData):
                if s_data.name == "":
                    kg_qa_result.append(s_data.biz_id)
                else:
                    kg_qa_result.append(s_data.name)
            if isinstance(s_data, RelationData):
                kg_qa_result.append(str(s_data))
        process_info[logic_node.sub_query]["kg_answer"] += f"\n{';'.join(kg_qa_result)}"
        process_info["kg_solved_answer"].append(f"\n{';'.join(kg_qa_result)}")
        return process_info[logic_node.sub_query]
