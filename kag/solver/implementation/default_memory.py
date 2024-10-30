from tenacity import retry, stop_after_attempt

from kag.common.base.prompt_op import PromptOp
from kag.interface.solver.kag_memory_abc import KagMemoryABC


class DefaultMemory(KagMemoryABC):
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

    @retry(stop=stop_after_attempt(3))
    def _verifier(self, supporting_fact, sub_instruction):
        res = self.llm_module.invoke({'sub_instruction': sub_instruction,
                                      'supporting_fact': supporting_fact}, self.verify_prompt,
                                     with_json_parse=False, with_except=True)
        if res is None:
            return
        if res not in self.state_memory:
            self.state_memory.append(res)

    @retry(stop=stop_after_attempt(3))
    def _extractor(self, supporting_fact, instruction):
        if supporting_fact is None or supporting_fact == '':
            return
        evidence = self.llm_module.invoke({'supporting_fact': supporting_fact, 'instruction': instruction},
                                          self.extractor_prompt, with_json_parse=False, with_except=True)
        if evidence not in self.evidence_memory:
            self.evidence_memory.append(evidence)

    def save_memory(self, solved_answer, supporting_fact, instruction):
        if solved_answer != "":
            self.exact_answer.append(solved_answer)
            return
        # skip first instruction to verifier
        if len(self.instruction_set) != 0:
            self._verifier(supporting_fact, instruction)

        self._extractor(supporting_fact, instruction)
        self.instruction_set.append(instruction)

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