import logging

from tenacity import retry, stop_after_attempt

from kag.interface import KagBaseModule

from kag.solver.utils import init_prompt_with_fallback

logger = logging.getLogger()


class LFSubGenerator(KagBaseModule):
    """
    Generator class that selects different prompts based on the scenario to produce answers.
    This class can be extended to implement custom generation strategies.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.solve_question_prompt = init_prompt_with_fallback(
            "solve_question", self.biz_scene
        )
        self.solve_question_without_docs_prompt = init_prompt_with_fallback(
            "solve_question_without_docs", self.biz_scene
        )
        self.solve_question_without_spo_prompt = init_prompt_with_fallback(
            "solve_question_without_spo", self.biz_scene
        )

    @retry(stop=stop_after_attempt(3))
    def generate_sub_answer(
        self, question: str, knowledge_graph: [], docs: [], history=[]
    ):
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
        history_qa = []
        for i, item in enumerate(history):
            sub_answer = item.res.sub_answer
            if sub_answer and "i don't know" not in sub_answer.lower():
                history_qa.append(
                    f"query{i}: {item.res.sub_query} answer{i}:{sub_answer}"
                )
            else:
                history_qa.append(f"query{i}: {item.res.sub_answer}")
        if knowledge_graph:
            if len(docs) > 0:
                prompt = self.solve_question_prompt
                params = {
                    "question": question,
                    "knowledge_graph": str(knowledge_graph),
                    "docs": str(docs),
                    "history": "\n".join(history_qa),
                }
            else:
                prompt = self.solve_question_without_docs_prompt
                params = {
                    "question": question,
                    "knowledge_graph": str(knowledge_graph),
                    "history": "\n".join(history_qa),
                }
        else:
            prompt = self.solve_question_without_spo_prompt
            params = {
                "question": question,
                "docs": str(docs),
                "history": "\n".join(history_qa),
            }
        llm_output = self.llm_module.invoke(
            params, prompt, with_json_parse=False, with_except=True
        )
        logger.debug(
            f"sub_question:{question}\n sub_answer:{llm_output} prompt:\n{prompt}"
        )
        if llm_output:
            return llm_output
        return "I don't know"
