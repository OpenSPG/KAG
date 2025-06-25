import logging
from tenacity import retry, stop_after_attempt

from kag.interface import PromptABC
from kag.interface import LLMClient
from kag.interface.solver.kag_memory_abc import KagMemoryABC
from kag.interface.solver.base_model import LFExecuteResult
from kag.solver.utils import init_prompt_with_fallback

logger = logging.getLogger()
from kag.examples.finqa.reasoner.common import (
    get_history_context_info_list,
    get_history_context_str,
    get_all_recall_docs,
    get_execute_context,
)


@KagMemoryABC.register("finqa_memory", as_default=True)
class FinQAMemory(KagMemoryABC):
    def __init__(
        self,
        llm_client: LLMClient = None,
        **kwargs,
    ):
        super().__init__(llm_client, **kwargs)

        self.state_memory = []
        self.evidence_memory = []
        self.exact_answer = []
        self.instruction_set = []
        self.lf_res = []
        self.row_instruction = None

    def save_memory(
        self, solved_answer, supporting_fact, instruction, lf_res: LFExecuteResult
    ):
        if solved_answer:
            self.exact_answer.append(solved_answer)
            return
        self.evidence_memory.append(supporting_fact)
        self.instruction_set.append(instruction)
        if self.row_instruction is None:
            self.row_instruction = instruction
        self.lf_res = lf_res

    def get_solved_answer(self):
        return self.exact_answer[-1] if len(self.exact_answer) > 0 else None

    def serialize_memory(self):
        context_list = get_execute_context(
            question=self.row_instruction,
            execute_rst_list=self.lf_res.execute_rst_list,
            with_code=False,
        )
        context_str = get_history_context_str(context_list=context_list)
        return context_str

    def refresh(self):
        self.state_memory = []
        self.evidence_memory = []
        self.exact_answer = []
