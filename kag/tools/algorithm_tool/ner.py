from typing import List

from kag.interface import ToolABC
from kag.interface.solver.base_model import SPOEntity


@ToolABC.register("ner")
class Ner(ToolABC):
    def __init__(self):
        super().__init__()

    def invoke(self, query, **kwargs) -> List[SPOEntity]:
        raise NotImplementedError("invoke not implemented yet.")

    def schema(self):
        return {
            "name": "ner",
            "description": "Identify named entities in the input text",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The text to analyze for named entities"
                    }
                },
                "required": ["query"]
            }
        }
