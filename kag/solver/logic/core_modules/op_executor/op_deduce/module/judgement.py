from kag.common.base.prompt_op import PromptOp
from kag.solver.logic.core_modules.common.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.op_executor.op_executor import OpExecutor


class JudgementOp(OpExecutor):
    def __init__(self, nl_query: str, kg_graph: KgGraph, schema: SchemaUtils, debug_info: dict):
        super().__init__(nl_query, kg_graph, schema, debug_info)
        self.prompt = PromptOp.load(self.biz_scene, "deduce_judge")(
            language=self.language
        )

    def executor(self, logic_node: LogicNode, req_id: str, param: dict) -> list:
        history_qa_pair = self.debug_info.get("sub_qa_pair", [])
        qa_pair = "\n".join([f"Q: {q}\nA: {a}" for q, a in history_qa_pair])
        spo_info = self.kg_graph.to_evidence()
        information = str(spo_info) + "\n" + qa_pair
        if_answered, answer = self.llm_module.invoke({'instruction': self.nl_query, 'memory': information},
                                                     self.prompt, with_json_parse=False)
        return [if_answered, answer]