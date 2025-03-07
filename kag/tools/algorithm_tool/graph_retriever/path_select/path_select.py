from typing import List

from kag.interface import ToolABC
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData, RelationData
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode

@ToolABC.register("path_select")
class PathSelect(ToolABC):
    def __init__(self):
        super().__init__()

    def invoke(self, query, spo: GetSPONode, entity: EntityData, **kwargs) -> List[RelationData]:
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
                        "description": "Input text for path selection"
                    },
                    "spo": {
                        "type": "object",
                        "properties": {
                            "subject": {
                                "type": "string",
                                "description": "Subject entity in SPO triple"
                            },
                            "predicate": {
                                "type": "string",
                                "description": "Relationship type in SPO triple"
                            },
                            "object": {
                                "type": "string",
                                "description": "Object entity in SPO triple"
                            }
                        },
                        "required": ["subject", "predicate", "object"]
                    },
                    "entity": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Entity id in graph"
                            },
                            "name": {
                                "type": "string",
                                "description": "Starting entity name"
                            },
                            "type": {
                                "type": "string",
                                "description": "Entity type category"
                            }
                        },
                        "required": ["id", "type"]
                    }
                },
                "required": ["query", "spo", "entity"]
            }
        }
