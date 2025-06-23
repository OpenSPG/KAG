from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum

class SPGOntologyEnum(str, Enum):
    PROPERTY = "PROPERTY"
    RELATION = "RELATION"
    ENTITY = "ENTITY"
    CONCEPT = "CONCEPT"

class BasicInfo(BaseModel):
    name: str
    description: Optional[str] = None

class SPGTypeRef(BaseModel):
    name: str
    type_enum: SPGOntologyEnum

class PropertyRef(BaseModel):
    subject_type_ref: SPGTypeRef
    basic_info: BasicInfo
    object_type_ref: SPGTypeRef
    ontology_enum: SPGOntologyEnum
    project_id: Optional[int] = None
    ontology_id: Optional[int] = None

class BaseOntology(BaseModel):
    project_id: Optional[int] = None
    ontology_id: Optional[int] = None