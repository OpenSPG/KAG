from tenacity import retry, stop_after_attempt

from kag.interface import PromptABC
from kag.interface import LLMClient
from kag.interface.solver.kag_memory_abc import KagMemoryABC
from kag.interface.solver.kag_reflector_abc import KagReflectorABC
from kag.solver.implementation.default_reflector import DefaultReflector
from kag.solver.utils import init_prompt_with_fallback


@KagReflectorABC.register("finqa_reflector", as_default=True)
class FinQAReflector(DefaultReflector):
    def __init__(
        self,
        refine_prompt: PromptABC = None,
        judge_prompt: PromptABC = None,
        llm_client: LLMClient = None,
        **kwargs,
    ):
        super().__init__(refine_prompt, judge_prompt, llm_client, **kwargs)

    def reflect_query(self, memory: KagMemoryABC, instruction: str) -> (bool, str):
        """
        Reflects on the query and determines whether it can be answered.

        :param memory (KagMemory): The context or memory information to use for rewriting.
        :param instruction (str): The original instruction to be rewritten.
        :return: A tuple (can_answer, refined_query)
            - can_answer: Whether the query can be answered (boolean)
            - refined_query: The refined query (string)
        """
        can_answer = self._can_answer(memory, instruction)
        return can_answer, instruction
