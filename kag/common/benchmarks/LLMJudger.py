from kag.interface import LLMClient
from kag.common.conf import KAG_PROJECT_CONF
from kag.common.registry.registrable import Registrable
from kag.common.benchmarks.prompt.JudgerPrompt import JudgerPrompt

class LLMJudger(Registrable):

    def __int__(self, llm: LLMClient = None):
        self.llm = llm


    '''
        judge whether prediction is consistent with gold
    '''

    def judge_by_llm(self, question: str, prediction: str, gold: str):
        language = KAG_PROJECT_CONF.language
        prompt = JudgerPrompt(language)
        response = self.llm.invoke({"question": question, "prediction": prediction, "gold": gold}, prompt)
        return response
