from typing import List

from kag.interface import ToolABC
from kag.interface.solver.model.one_hop_graph import EntityData, RelationData
from kag.common.parser.logic_node_parser import GetSPONode


@ToolABC.register("path_select")
class PathSelect(ToolABC):
    def __init__(self):
        super().__init__()

    def invoke(
        self,
        query,
        spo: GetSPONode,
        heads: List[EntityData],
        tails: List[EntityData],
        **kwargs
    ) -> List[RelationData]:
        raise NotImplementedError("invoke not implemented yet.")

    def schema(self):
        return {
            "name": "path_select",
            "description": "Find valid paths in the knowledge graph starting from the given entity based on query and SPO structure",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Input text for path selection",
                    },
                    "spo": {
                        "type": "object",
                        "properties": {
                            "subject": {
                                "type": "string",
                                "description": "Subject entity in SPO triple",
                            },
                            "predicate": {
                                "type": "string",
                                "description": "Relationship type in SPO triple",
                            },
                            "object": {
                                "type": "string",
                                "description": "Object entity in SPO triple",
                            },
                        },
                        "required": ["subject", "predicate", "object"],
                    },
                    "heads": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "Entity id in graph",
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Starting entity name",
                                },
                                "type": {
                                    "type": "string",
                                    "description": "Entity type category",
                                },
                            },
                            "required": ["id", "type"],
                        },
                    },
                    "tails": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "Entity id in graph",
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Starting entity name",
                                },
                                "type": {
                                    "type": "string",
                                    "description": "Entity type category",
                                },
                            },
                            "required": ["id", "type"],
                        },
                    },
                },
                "required": ["query", "spo"],
            },
        }
