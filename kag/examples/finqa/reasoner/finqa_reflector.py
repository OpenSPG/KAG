from tenacity import retry, stop_after_attempt

from kag.interface import PromptABC
from kag.interface import LLMClient
from kag.interface.solver.kag_memory_abc import KagMemoryABC
from kag.interface.solver.kag_reflector_abc import KagReflectorABC
from kag.solver.utils import init_prompt_with_fallback
from kag.solver.implementation.default_reflector import DefaultReflector


@KagReflectorABC.register("finqa_reflector", as_default=True)
class FinQAReflector(DefaultReflector):
    def __init__(
        self,
        refine_prompt: PromptABC = None,
        judge_prompt: PromptABC = None,
        llm_client: LLMClient = None,
        **kwargs,
    ):
        super().__init__(
            refine_prompt=refine_prompt,
            judge_prompt=judge_prompt,
            llm_client=llm_client,
            **kwargs,
        )

    def _refine_query(self, memory: KagMemoryABC, instruction: str):
        return instruction
