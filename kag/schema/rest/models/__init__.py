# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

from __future__ import absolute_import

from kag.schema.rest.models.basic_info import BasicInfo
from kag.schema.rest.models.ontology_id import OntologyId
from kag.schema.rest.models.base_ontology import BaseOntology
from kag.schema.rest.models.user_info import UserInfo
from kag.schema.rest.models.predicate.relation import Relation
from kag.schema.rest.models.predicate.property import Property
from kag.schema.rest.models.predicate.property_ref import PropertyRef
from kag.schema.rest.models.predicate.mounted_concept_config import (
    MountedConceptConfig,
)
from kag.schema.rest.models.predicate.property_advanced_config import (
    PropertyAdvancedConfig,
)
from kag.schema.rest.models.predicate.sub_property import SubProperty
from kag.schema.rest.models.predicate.property_ref_basic_info import (
    PropertyRefBasicInfo,
)
from kag.schema.rest.models.predicate.sub_property_basic_info import (
    SubPropertyBasicInfo,
)
from kag.schema.rest.models.alter.schema_draft import SchemaDraft
from kag.schema.rest.models.alter.schema_alter_request import SchemaAlterRequest
from kag.schema.rest.models.type.base_spg_type import BaseSpgType
from kag.schema.rest.models.type.operator_key import OperatorKey
from kag.schema.rest.models.type.event_type import EventType
from kag.schema.rest.models.type.spg_type_ref_basic_info import SpgTypeRefBasicInfo
from kag.schema.rest.models.type.entity_type import EntityType
from kag.schema.rest.models.type.spg_type_advanced_config import SpgTypeAdvancedConfig
from kag.schema.rest.models.type.concept_type import ConceptType
from kag.schema.rest.models.type.base_advanced_type import BaseAdvancedType
from kag.schema.rest.models.type.concept_layer_config import ConceptLayerConfig
from kag.schema.rest.models.type.multi_version_config import MultiVersionConfig
from kag.schema.rest.models.type.standard_type_basic_info import StandardTypeBasicInfo
from kag.schema.rest.models.type.parent_type_info import ParentTypeInfo
from kag.schema.rest.models.type.project_schema import ProjectSchema
from kag.schema.rest.models.type.concept_taxonomic_config import (
    ConceptTaxonomicConfig,
)
from kag.schema.rest.models.type.standard_type import StandardType
from kag.schema.rest.models.type.spg_type_ref import SpgTypeRef
from kag.schema.rest.models.type.basic_type import BasicType
from kag.schema.rest.models.identifier.spg_type_identifier import SpgTypeIdentifier
from kag.schema.rest.models.identifier.base_spg_identifier import BaseSpgIdentifier
from kag.schema.rest.models.identifier.concept_identifier import ConceptIdentifier
from kag.schema.rest.models.identifier.operator_identifier import OperatorIdentifier
from kag.schema.rest.models.identifier.spg_triple_identifier import (
    SpgTripleIdentifier,
)
from kag.schema.rest.models.identifier.predicate_identifier import PredicateIdentifier
from kag.schema.rest.models.concept.remove_logical_causation_request import (
    RemoveLogicalCausationRequest,
)
from kag.schema.rest.models.concept.define_logical_causation_request import (
    DefineLogicalCausationRequest,
)
from kag.schema.rest.models.concept.remove_dynamic_taxonomy_request import (
    RemoveDynamicTaxonomyRequest,
)
from kag.schema.rest.models.concept.define_dynamic_taxonomy_request import (
    DefineDynamicTaxonomyRequest,
)
from kag.schema.rest.models.semantic.base_semantic import BaseSemantic
from kag.schema.rest.models.semantic.predicate_semantic import PredicateSemantic
from kag.schema.rest.models.semantic.rule_code import RuleCode
from kag.schema.rest.models.semantic.logical_rule import LogicalRule
from kag.schema.rest.models.operator.operator_version_response import (
    OperatorVersionResponse,
)
from kag.schema.rest.models.operator.operator_version_request import (
    OperatorVersionRequest,
)
from kag.schema.rest.models.operator.operator_overview import OperatorOverview
from kag.schema.rest.models.operator.operator_version import OperatorVersion
from kag.schema.rest.models.operator.operator_create_response import (
    OperatorCreateResponse,
)
from kag.schema.rest.models.operator.operator_create_request import (
    OperatorCreateRequest,
)
from kag.schema.rest.models.constraint.constraint import Constraint
from kag.schema.rest.models.constraint.base_constraint_item import BaseConstraintItem
from kag.schema.rest.models.constraint.multi_val_constraint import MultiValConstraint
from kag.schema.rest.models.constraint.regular_constraint import RegularConstraint
from kag.schema.rest.models.constraint.not_null_constraint import NotNullConstraint
from kag.schema.rest.models.constraint.enum_constraint import EnumConstraint
