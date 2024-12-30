from tenacity import retry, stop_after_attempt

from kag.common.base.prompt_op import PromptOp
from kag.interface.solver.kag_reflector_abc import KagMemoryABC
from kag.interface.solver.kag_reflector_abc import KagReflectorABC


class SPOReflector(KagReflectorABC):
    def __init__(self, **kwargs):
        """
        A class for rewriting instructions based on provided memory information.

        Attributes:
        - llm_module (Any): The LLM module to be used by this instance.
        - rewrite_prompt (PromptOp): The prompt operation for rewriting responses.
        """
        super().__init__(**kwargs)
    @retry(stop=stop_after_attempt(3))
    def _can_answer(self, memory: KagMemoryABC, instruction: str):
        return True
    @retry(stop=stop_after_attempt(3))
    def _refine_query(self, memory: KagMemoryABC, instruction: str):
        return instruction