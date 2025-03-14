import logging
from tenacity import retry, stop_after_attempt

from kag.interface import PromptABC
from kag.interface import LLMClient
from kag.interface.solver.kag_memory_abc import KagMemoryABC
from kag.interface.solver.base_model import LFExecuteResult
from kag.solver.utils import init_prompt_with_fallback

logger = logging.getLogger()


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

    def save_memory(
        self, solved_answer, supporting_fact, instruction, lf_res: LFExecuteResult
    ):
        if solved_answer:
            self.exact_answer.append(solved_answer)
            return
        self.evidence_memory.append(supporting_fact)
        self.instruction_set.append(instruction)
        self.lf_res = lf_res

    def get_solved_answer(self):
        return self.exact_answer[-1] if len(self.exact_answer) > 0 else None

    def serialize_memory(self):
        if len(self.exact_answer) > 0:
            return f"[Solved Answer]{self.exact_answer[-1]}"
        serialize_memory = "[Evidence Memory]:{}\n".format(
            "\n".join(self.evidence_memory)
        )
        return serialize_memory

    def refresh(self):
        self.state_memory = []
        self.evidence_memory = []
        self.exact_answer = []
