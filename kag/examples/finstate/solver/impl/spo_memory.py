from tenacity import retry, stop_after_attempt

from kag.common.base.prompt_op import PromptOp
from kag.interface.solver.kag_memory_abc import KagMemoryABC


class SpoMemory(KagMemoryABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.verify_prompt = PromptOp.load(self.biz_scene, "resp_verifier")(
            language=self.language
        )
        self.extractor_prompt = PromptOp.load(self.biz_scene, "resp_extractor")(
            language=self.language
        )
        self.state_memory = []
        self.evidence_memory = []
        self.exact_answer = []
        self.instruction_set = []
    def save_memory(self, solved_answer, supporting_fact, instruction):
        if solved_answer != "":
            self.exact_answer.append(solved_answer)
            return
        self.evidence_memory.append(supporting_fact)

    def get_solved_answer(self):
        return self.exact_answer[-1] if len(self.exact_answer) > 0 else None

    def serialize_memory(self):
        if len(self.exact_answer) > 0:
            return f"[Solved Answer]{self.exact_answer[-1]}"
        serialize_memory = "[State Memory]:{}\n[Evidence Memory]:{}\n".format(
            str(self.state_memory), str(self.evidence_memory)
        )
        return serialize_memory

    def refresh(self):
        self.state_memory = []
        self.evidence_memory = []
        self.exact_answer = []