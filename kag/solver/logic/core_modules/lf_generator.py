import logging

from kag.common.base.prompt_op import PromptOp
from kag.solver.common.base import KagBaseModule

logger = logging.getLogger(__name__)


class LFGenerator(KagBaseModule):
    """
    Generator class that selects different prompts based on the scenario to produce answers.
    This class can be extended to implement custom generation strategies.
    """

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.solve_question_prompt = PromptOp.load(self.biz_scene, "solve_question")(
            language=self.language
        )

        self.solve_question_without_docs_prompt = PromptOp.load(self.biz_scene, "solve_question_without_docs")(
            language=self.language
        )

        self.solve_question_without_spo_prompt = PromptOp.load(self.biz_scene, "solve_question_without_spo")(
            language=self.language
        )

    def generate_sub_answer(self, question: str, knowledge_graph: [], docs: [], history=[]):
        """
        Generates a sub-answer based on the given question, knowledge graph, documents, and history.

        Parameters:
        question (str): The main question to answer.
        knowledge_graph (list): A list of knowledge graph data.
        docs (list): A list of documents related to the question.
        history (list, optional): A list of previous query-answer pairs. Defaults to an empty list.

        Returns:
        str: The generated sub-answer.
        """
        history_qa = [f"query{i}: {item['sub_query']}\nanswer{i}: {item['sub_answer']}" for i, item in
                      enumerate(history)]
        if knowledge_graph:
            if len(docs) > 0:
                prompt = self.solve_question_prompt
                params = {
                    'question': question,
                    'knowledge_graph': str(knowledge_graph),
                    'docs': str(docs),
                    'history': '\n'.join(history_qa)
                }
            else:
                prompt = self.solve_question_without_docs_prompt
                params = {
                    'question': question,
                    'knowledge_graph': str(knowledge_graph),
                    'history': '\n'.join(history_qa)
                }
        else:
            prompt = self.solve_question_without_spo_prompt
            params = {
                'question': question,
                'docs': str(docs),
                'history': '\n'.join(history_qa)
            }
        llm_output = self.llm_module.invoke(params, prompt, with_json_parse=False, with_except=True)
        logger.debug(f"sub_question:{question}\n sub_answer:{llm_output} prompt:\n{prompt}")
        if llm_output:
            return llm_output
        return "I don't know"
