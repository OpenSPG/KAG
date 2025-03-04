import logging
from tenacity import stop_after_attempt, retry

from kag.interface.solver.kag_generator_abc import KAGGeneratorABC
from kag.solver.utils import init_prompt_with_fallback
from kag.interface import PromptABC
from kag.interface import LLMClient
from kag.solver.implementation.default_memory import DefaultMemory


@KAGGeneratorABC.register("default_generator", as_default=True)
class DefaultGenerator(KAGGeneratorABC):
    """
    The Generator class is an abstract base class for generating responses using a language model module.
    It initializes prompts for judging and generating responses based on the business scene and language settings.
    """

    def __init__(
        self, generate_prompt: PromptABC = None, llm_client: LLMClient = None, **kwargs
    ):
        super().__init__(llm_client, **kwargs)
        if generate_prompt is None:
            generate_prompt = init_prompt_with_fallback(
                "resp_generator", self.biz_scene
            )
        self.generate_prompt = generate_prompt

    @retry(stop=stop_after_attempt(3))
    def generate(self, instruction, memory: DefaultMemory):
        solved_answer = memory.get_solved_answer()
        if solved_answer is not None:
            return solved_answer
        present_memory = memory.serialize_memory()
        return self.llm_module.invoke(
            {"memory": present_memory, "instruction": instruction},
            self.generate_prompt,
            with_json_parse=False,
            with_except=True,
        )
