from tenacity import retry, stop_after_attempt

from kag.common.base.prompt_op import PromptOp
from kag.interface.solver.kag_reflector_abc import KagMemoryABC
from kag.interface.solver.kag_reflector_abc import KagReflectorABC


class DefaultReflector(KagReflectorABC):
    def __init__(self, **kwargs):
        """
        A class for rewriting instructions based on provided memory information.

        Attributes:
        - llm_module (Any): The LLM module to be used by this instance.
        - rewrite_prompt (PromptOp): The prompt operation for rewriting responses.
        """
        super().__init__(**kwargs)
        self.refine_prompt = PromptOp.load(self.biz_scene, "resp_reflector")(
            language=self.language
        )

        self.judge_prompt = PromptOp.load(self.biz_scene, "resp_judge")(
            language=self.language
        )

    def _get_serialize_memory(self, memory: KagMemoryABC):
        if memory is None:
            return ""
        return memory.serialize_memory()

    @retry(stop=stop_after_attempt(3))
    def _can_answer(self, memory: KagMemoryABC, instruction: str):
        """
        Determines whether the query can be answered.

        :param memory (KagMemory): The context or memory information to use for rewriting.
        :param instruction (str): The original instruction to be rewritten.
        :return: Whether the query can be answered (boolean)
        """
        serialize_memory = self._get_serialize_memory(memory)
        if serialize_memory == "":
            return False

        if memory.get_solved_answer() != "":
            return True

        return self.llm_module.invoke({'memory': serialize_memory, 'instruction': instruction}, self.judge_prompt,
                                      with_json_parse=False, with_except=True)

    @retry(stop=stop_after_attempt(3))
    def _refine_query(self, memory: KagMemoryABC, instruction: str):
        """
        Refines the query.

        :param memory (KagMemory): The context or memory information to use for rewriting.
        :param instruction (str): The original instruction to be rewritten.
        :return: The refined query (string)
        """
        serialize_memory = self._get_serialize_memory(memory)
        if serialize_memory == "":
            return instruction

        update_reason_path = self.llm_module.invoke({"memory": serialize_memory, "instruction": instruction},
                                                    self.refine_prompt,
                                                    with_json_parse=False, with_except=True)
        if len(update_reason_path) == 0:
            return None
        return update_reason_path[0]