from tenacity import retry, stop_after_attempt

from kag.interface import PromptABC
from kag.interface import LLMClient
from kag.interface.solver.kag_memory_abc import KagMemoryABC
from kag.interface.solver.kag_reflector_abc import KagReflectorABC
from kag.solver.utils import init_prompt_with_fallback

from kag.interface.solver.base_model import LFPlan

from kag.interface.solver.base_model import LFExecuteResult


from kag.examples.finqa.reasoner.finqa_memory import FinQAMemory
from kag.examples.finqa.reasoner.common import (
    get_history_context_info_list,
    get_history_context_str,
    get_all_recall_docs,
    get_execute_context,
)


@KagReflectorABC.register("finqa_reflector", as_default=True)
class FinQAReflector(KagReflectorABC):
    def __init__(
        self,
        refine_prompt: PromptABC = None,
        judge_prompt: PromptABC = None,
        llm_client: LLMClient = None,
        **kwargs,
    ):
        """
        A class for rewriting instructions based on provided memory information.

        Attributes:
        - llm_module (Any): The LLM module to be used by this instance.
        - rewrite_prompt (PromptABC): The prompt operation for rewriting responses.
        """
        super().__init__(llm_client=llm_client, **kwargs)
        if refine_prompt is None:
            refine_prompt = init_prompt_with_fallback("resp_reflector", self.biz_scene)
        self.refine_prompt = refine_prompt

        if judge_prompt is None:
            judge_prompt = init_prompt_with_fallback("resp_judge", self.biz_scene)
        self.judge_prompt = judge_prompt

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
        memory: FinQAMemory = memory
        recall_docs = get_all_recall_docs(memory.lf_res.execute_rst_list)
        if len(recall_docs) <= 0:
            # 无数据召回
            return False

        for _, exe_info in enumerate(memory.lf_res.execute_rst_list):
            exe_info: LFExecuteResult = exe_info
            for _, lf_plan in enumerate(exe_info.sub_plans):
                lf_plan: LFPlan = lf_plan
                if lf_plan.sub_query_type != "math":
                    continue

        serialize_memory = self._get_serialize_memory(memory)
        if serialize_memory == "":
            return False

        if memory.get_solved_answer():
            return True

        return self.llm_module.invoke(
            {"memory": serialize_memory, "instruction": instruction},
            self.judge_prompt,
            with_json_parse=False,
            with_except=True,
        )

    @retry(stop=stop_after_attempt(3))
    def _refine_query(self, memory: KagMemoryABC, instruction: str):
        return instruction
