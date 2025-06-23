from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from models.base import BaseOntology, BasicInfo, SPGTypeRef, SPGOntologyEnum

class Property(BaseModel):
    name: str
    value_type: str
    description: Optional[str] = None

class Relation(BaseModel):
    name: str
    target_type: str
    properties: List[Property] = []

class EntityType(BaseOntology):
    basic_info: BasicInfo
    properties: List[Property] = []
    relations: List[Relation] = []
    type_enum: SPGOntologyEnum = SPGOntologyEnum.ENTITY

    def to_ref(self) -> SPGTypeRef:
        return SPGTypeRef(
            name=self.basic_info.name,
            type_enum=self.type_enum
        )

class EntityInstance(BaseModel):
    id: str
    type_name: str
    properties: Dict[str, Any]
    relations: List['RelationInstance'] = []

class RelationInstance(BaseModel):
    src_id: str
    dst_id: str
    relation_type: str
    properties: Dict[str, Any] = {}