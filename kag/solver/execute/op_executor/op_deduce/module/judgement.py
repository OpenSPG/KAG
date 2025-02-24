from typing import Dict, List

from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.interface.solver.base_model import LFPlan
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils

from kag.solver.utils import init_prompt_with_fallback


class JudgementOp(OpExecutor):
    def __init__(
        self,
        schema: SchemaUtils,
        **kwargs,
    ):
        super().__init__(schema, **kwargs)
        self.prompt = init_prompt_with_fallback("deduce_judge", self.biz_scene)

    def executor(self, nl_query: str, lf_plan: LFPlan, req_id: str, kg_graph: KgGraph, process_info: dict,
                 history: List[LFPlan], param: dict) -> Dict:
        history_qa_pair = process_info.get("sub_qa_pair", [])
        input_contents = process_info[lf_plan.lf_node.sub_query].get("input_contents", '')
        content = input_contents if input_contents else "\n".join([f"Q: {q}\nA: {a}" for q, a in history_qa_pair])
        if_answered, answer = self.llm_module.invoke(
            {"instruction": lf_plan.lf_node.sub_query, "memory": content},
            self.prompt,
            with_json_parse=False,
            with_except=True,
        )
        return {"if_answered": if_answered, "answer": answer}
