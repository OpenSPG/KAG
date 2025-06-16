from kag.interface import LLMClient
from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.common.benchmarks.prompt.JudgerPrompt import JudgerPrompt


class LLMJudger:
    def __init__(self, llm: LLMClient = None, **kwargs):
        self.llm = llm
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        self.kag_project_config = kag_config.global_config

    """
        judge whether prediction is consistent with gold
    """

    def judge_by_llm(self, question: str, prediction: str, gold: str):
        language = self.kag_project_config.language
        prompt = JudgerPrompt(language)
        response = self.llm.invoke(
            {"question": question, "prediction": prediction, "gold": gold}, prompt
        )
        return response
