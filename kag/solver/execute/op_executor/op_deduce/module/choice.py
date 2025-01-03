from typing import Dict

from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.interface.solver.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.utils import init_prompt_with_fallback


class ChoiceOp(OpExecutor):
    def __init__(
        self,
        schema: SchemaUtils,
        **kwargs,
    ):
        super().__init__(schema, **kwargs)
        self.prompt = init_prompt_with_fallback("deduce_choice", self.biz_scene)

    def executor(
        self,
        nl_query: str,
        logic_node: LogicNode,
        req_id: str,
        kg_graph: KgGraph,
        process_info: dict,
        param: dict,
    ) -> Dict:
        # get history qa pair from debug_info
        history_qa_pair = process_info.get("sub_qa_pair", [])
        qa_pair = "\n".join([f"Q: {q}\nA: {a}" for q, a in history_qa_pair])
        if_answered, answer = self.llm_module.invoke(
            {"instruction": logic_node.sub_query, "memory": qa_pair},
            self.prompt,
            with_json_parse=False,
            with_except=True,
        )
        return {"if_answered": if_answered, "answer": answer}
