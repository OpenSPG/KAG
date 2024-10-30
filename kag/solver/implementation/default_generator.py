from tenacity import stop_after_attempt, retry

from kag.common.base.prompt_op import PromptOp
from kag.interface.solver.kag_generator_abc import KAGGeneratorABC
from kag.solver.implementation.default_memory import DefaultMemory


class DefaultGenerator(KAGGeneratorABC):
    """
     The Generator class is an abstract base class for generating responses using a language model module.
     It initializes prompts for judging and generating responses based on the business scene and language settings.
     """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.generate_prompt = PromptOp.load(self.biz_scene, "resp_generator")(
            language=self.language
        )

    @retry(stop=stop_after_attempt(3))
    def generate(self, instruction, memory: DefaultMemory):
        solved_answer = memory.get_solved_answer()
        if solved_answer is not None:
            return solved_answer
        present_memory = memory.serialize_memory()
        return self.llm_module.invoke({'memory': present_memory, 'instruction': instruction}, self.generate_prompt, with_json_parse=False, with_except=True)
