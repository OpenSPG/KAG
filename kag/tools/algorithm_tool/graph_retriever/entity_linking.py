from typing import List

from kag.interface import ToolABC
from kag.interface.solver.base_model import SPOEntity
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData


@ToolABC.register("entity_linking")
class EntityLinking(ToolABC):
    def __init__(self):
        super().__init__()

    def invoke(self, query, entity: SPOEntity, **kwargs) -> List[EntityData]:
        raise NotImplementedError("invoke not implemented yet.")

    def schema(self):
        return {
            "name": "entity_linking",
            "description": "Link entities in input text to corresponding entities in knowledge graph",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Original text that needs entity linking"
                    },
                    "entity": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Name of the entity to be linked"
                            },
                            "type": {
                                "type": "string",
                                "description": "Entity type, such as person, location, organization, etc."
                            }
                        },
                        "required": ["name", "type"]
                    }
                },
                "required": ["query", "entity"]
            }
        }

