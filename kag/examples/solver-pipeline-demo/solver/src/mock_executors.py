from typing import List
from kag.interface import ExecutorABC, LLMClient


@ExecutorABC.register("kg_retriever")
class KGReteirver(ExecutorABC):
    def __init__(self):
        pass

    def invoke(self, query: str, context: List[str], **kwargs):
        return ["hello!"]

    def call_kg_retriever(self, query: str, context: List[str], **kwargs):
        return self.invoke(query, context, **kwargs)

    def schema(self):
        return {
            "name": "call_kg_retriever",
            "arguments": {
                "query": {"type": "str", "description": "The search query string."}
            },
        }


@ExecutorABC.register("py_code_generator")
class PYCodeGenerator(ExecutorABC):
    def __init__(self):
        pass

    def generate_code(self, query: str, context: List[str], **kwargs):
        return "print(123)"

    def invoke(self, query: str, context: List[str], **kwargs):
        code = self.generate_code(query, context, **kwargs)
        return eval(code)

    def call_py_code_generator(self, query: str, context: List[str], **kwargs):
        return self.invoke(query, context, **kwargs)

    def schema(self):
        return {
            "name": "call_py_code_generator",
            "arguments": {
                "query": {"type": "str", "description": "The task description."}
            },
        }


@ExecutorABC.register("deepseek")
class DeepseekAgent(ExecutorABC):
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def invoke(self, query: str, context: List[str], **kwargs):
        return f"{query}{context}"

    def schema(self):
        return {
            "name": "call_deepseek",
            "arguments": {
                "query": {"type": "str", "description": "The task description."}
            },
        }
