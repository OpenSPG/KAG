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

from knext.schema.rest.models.basic_info import BasicInfo
from knext.schema.rest.models.ontology_id import OntologyId
from knext.schema.rest.models.base_ontology import BaseOntology
from knext.schema.rest.models.user_info import UserInfo
from knext.schema.rest.models.predicate.relation import Relation
from knext.schema.rest.models.predicate.property import Property
from knext.schema.rest.models.predicate.property_ref import PropertyRef
from knext.schema.rest.models.predicate.mounted_concept_config import (
    MountedConceptConfig,
)
from knext.schema.rest.models.predicate.property_advanced_config import (
    PropertyAdvancedConfig,
)
from knext.schema.rest.models.predicate.sub_property import SubProperty
from knext.schema.rest.models.predicate.property_ref_basic_info import (
    PropertyRefBasicInfo,
)
from knext.schema.rest.models.predicate.sub_property_basic_info import (
    SubPropertyBasicInfo,
)
from knext.schema.rest.models.alter.schema_draft import SchemaDraft
from knext.schema.rest.models.alter.schema_alter_request import SchemaAlterRequest
from knext.schema.rest.models.type.base_spg_type import BaseSpgType
from knext.schema.rest.models.type.operator_key import OperatorKey
from knext.schema.rest.models.type.event_type import EventType
from knext.schema.rest.models.type.spg_type_ref_basic_info import SpgTypeRefBasicInfo
from knext.schema.rest.models.type.entity_type import EntityType
from knext.schema.rest.models.type.spg_type_advanced_config import SpgTypeAdvancedConfig
from knext.schema.rest.models.type.concept_type import ConceptType
from knext.schema.rest.models.type.base_advanced_type import BaseAdvancedType
from knext.schema.rest.models.type.concept_layer_config import ConceptLayerConfig
from knext.schema.rest.models.type.multi_version_config import MultiVersionConfig
from knext.schema.rest.models.type.standard_type_basic_info import StandardTypeBasicInfo
from knext.schema.rest.models.type.parent_type_info import ParentTypeInfo
from knext.schema.rest.models.type.project_schema import ProjectSchema
from knext.schema.rest.models.type.concept_taxonomic_config import (
    ConceptTaxonomicConfig,
)
from knext.schema.rest.models.type.standard_type import StandardType
from knext.schema.rest.models.type.spg_type_ref import SpgTypeRef
from knext.schema.rest.models.type.basic_type import BasicType
from knext.schema.rest.models.identifier.spg_type_identifier import SpgTypeIdentifier
from knext.schema.rest.models.identifier.base_spg_identifier import BaseSpgIdentifier
from knext.schema.rest.models.identifier.concept_identifier import ConceptIdentifier
from knext.schema.rest.models.identifier.operator_identifier import OperatorIdentifier
from knext.schema.rest.models.identifier.spg_triple_identifier import (
    SpgTripleIdentifier,
)
from knext.schema.rest.models.identifier.predicate_identifier import PredicateIdentifier
from knext.schema.rest.models.concept.remove_logical_causation_request import (
    RemoveLogicalCausationRequest,
)
from knext.schema.rest.models.concept.define_logical_causation_request import (
    DefineLogicalCausationRequest,
)
from knext.schema.rest.models.concept.remove_dynamic_taxonomy_request import (
    RemoveDynamicTaxonomyRequest,
)
from knext.schema.rest.models.concept.define_dynamic_taxonomy_request import (
    DefineDynamicTaxonomyRequest,
)
from knext.schema.rest.models.semantic.base_semantic import BaseSemantic
from knext.schema.rest.models.semantic.predicate_semantic import PredicateSemantic
from knext.schema.rest.models.semantic.rule_code import RuleCode
from knext.schema.rest.models.semantic.logical_rule import LogicalRule
from knext.schema.rest.models.operator.operator_version_response import (
    OperatorVersionResponse,
)
from knext.schema.rest.models.operator.operator_version_request import (
    OperatorVersionRequest,
)
from knext.schema.rest.models.operator.operator_overview import OperatorOverview
from knext.schema.rest.models.operator.operator_version import OperatorVersion
from knext.schema.rest.models.operator.operator_create_response import (
    OperatorCreateResponse,
)
from knext.schema.rest.models.operator.operator_create_request import (
    OperatorCreateRequest,
)
from knext.schema.rest.models.constraint.constraint import Constraint
from knext.schema.rest.models.constraint.base_constraint_item import BaseConstraintItem
from knext.schema.rest.models.constraint.multi_val_constraint import MultiValConstraint
from knext.schema.rest.models.constraint.regular_constraint import RegularConstraint
from knext.schema.rest.models.constraint.not_null_constraint import NotNullConstraint
from knext.schema.rest.models.constraint.enum_constraint import EnumConstraint
