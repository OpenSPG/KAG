# -*- coding: utf-8 -*-
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
import os
import re
from enum import Enum
from pathlib import Path

from knext.schema.model.base import (
    HypernymPredicateEnum,
    BasicTypeEnum,
    ConstraintTypeEnum,
    AlterOperationEnum,
    SpgTypeEnum,
    PropertyGroupEnum,
    IndexTypeEnum,
)
from knext.schema.model.spg_type import (
    EntityType,
    ConceptType,
    EventType,
    StandardType,
    Property,
    Relation,
    BasicType,
)
from knext.schema.client import SchemaClient


class IndentLevel(Enum):
    # Define entity/concept/event/standard types or subtypes
    Type = 0

    # Define description/properties/relations of type
    TypeMeta = 1

    # Define property/relation name of type
    Predicate = 2

    # Define description/constraint/rule/index of property/relation
    PredicateMeta = 3

    # Define property about property
    SubProperty = 4

    # Define constraint of sub property
    SubPropertyMeta = 5


class RegisterUnit(Enum):
    Type = "type"
    Property = "property"
    Relation = "relation"
    SubProperty = "subProperty"


class SPGSchemaMarkLang:
    """
    SPG Schema Mark Language Parser
    Feature1: parse schema script and then alter the schema of project
    Feature2: export schema script from a project
    """

    internal_type = set()
    entity_internal_property = set()
    event_internal_property = {"eventTime"}
    concept_internal_property = {"stdId", "alias"}
    keyword_type = {
        "EntityType",
        "ConceptType",
        "EventType",
        "StandardType",
        "BasicType",
    }
    semantic_rel = {
        "SYNANT": [
            "synonym",
            "antonym",
            "symbolOf",
            "distinctFrom",
            "definedAs",
            "locatedNear",
            "similarTo",
            "etymologicallyRelatedTo",
        ],
        "CAU": ["leadTo", "causes", "obstructedBy", "createdBy", "causesDesire"],
        "SEQ": [
            "happenedBefore",
            "hasSubevent",
            "hasFirstSubevent",
            "hasLastSubevent",
            "hasPrerequisite",
        ],
        "IND": ["belongTo"],
        "INC": ["isPartOf", "hasA", "madeOf", "derivedFrom", "hasContext"],
        "USE": ["usedFor", "capableOf", "receivesAction", "motivatedByGoal"],
    }
    semantic_rel_zh = {
        "synonym": "同义",
        "antonym": "反义",
        "symbolOf": "象征",
        "distinctFrom": "区别于",
        "definedAs": "定义为",
        "locatedNear": "位置临近",
        "similarTo": "类似于",
        "etymologicallyRelatedTo": "词源相关",
        "leadTo": "导致",
        "causes": "引起",
        "obstructedBy": "受阻于",
        "createdBy": "由...创建",
        "causesDesire": "引发欲望",
        "happenedBefore": "先于...发生",
        "hasSubevent": "拥有子事件",
        "hasFirstSubevent": "以...作为开始",
        "hasLastSubevent": "以...作为结束",
        "hasPrerequisite": "有前提条件",
        "belongTo": "属于",
        "isPartOf": "是...的一部分",
        "hasA": "拥有",
        "madeOf": "由…制成",
        "derivedFrom": "源自于",
        "hasContext": "有上下文",
        "usedFor": "用于",
        "capableOf": "能够",
        "receivesAction": "接受动作",
        "motivatedByGoal": "目标驱动",
    }
    parsing_register = {
        RegisterUnit.Type: None,
        RegisterUnit.Property: None,
        RegisterUnit.Relation: None,
        RegisterUnit.SubProperty: None,
    }
    indent_level_pos = [None, None, None, None, None, None]
    rule_quote_predicate = None
    rule_quote_open = False
    current_parsing_level = 0
    last_indent_level = 0
    namespace = None
    types = {}
    defined_types = {}

    def __init__(self, filename, with_server=True):
        self.reset()
        self.schema_file = filename
        self.current_line_num = 0
        if with_server:
            self.schema = SchemaClient()
            thing = self.schema.query_spg_type("Thing")
            for prop in thing.properties:
                self.entity_internal_property.add(prop)
                self.event_internal_property.add(prop)
                self.concept_internal_property.add(prop)
            session = self.schema.create_session()
            for type_name in session.spg_types:
                spg_type = session.get(type_name)
                if session.get(type_name).spg_type_enum in [
                    SpgTypeEnum.Basic,
                    SpgTypeEnum.Standard,
                ]:
                    self.internal_type.add(spg_type.name)
        else:
            self.internal_type = {"Text", "Float", "Integer"}
        self.load_script()

    def reset(self):
        self.internal_type = set()
        self.entity_internal_property = set()
        self.event_internal_property = {"eventTime"}
        self.concept_internal_property = {"stdId", "alias"}
        self.keyword_type = {
            "EntityType",
            "ConceptType",
            "EventType",
            "StandardType",
            "BasicType",
        }

        self.parsing_register = {
            RegisterUnit.Type: None,
            RegisterUnit.Property: None,
            RegisterUnit.Relation: None,
            RegisterUnit.SubProperty: None,
        }
        self.indent_level_pos = [None, None, None, None, None, None]
        self.rule_quote_predicate = None
        self.rule_quote_open = False
        self.current_parsing_level = 0
        self.last_indent_level = 0
        self.namespace = None
        self.types = {}

    def save_register(self, element: RegisterUnit, value):
        """
        maintain the session for parsing
        """

        self.parsing_register[element] = value
        if element == RegisterUnit.Type:
            self.parsing_register[RegisterUnit.Property] = None
            self.parsing_register[RegisterUnit.Relation] = None
            self.parsing_register[RegisterUnit.SubProperty] = None
        elif element == RegisterUnit.Property:
            self.parsing_register[RegisterUnit.Relation] = None
            self.parsing_register[RegisterUnit.SubProperty] = None
        elif element == RegisterUnit.Relation:
            self.parsing_register[RegisterUnit.Property] = None
            self.parsing_register[RegisterUnit.SubProperty] = None

    def adjust_parsing_level(self, step):
        """
        mark the indent level and clear related session
        """

        if step == 0:
            self.current_parsing_level = IndentLevel.Type.value
            # finish type parsing, clear the field in session
            self.save_register(RegisterUnit.Type, None)
            return
        if step < 0:
            self.current_parsing_level = max(0, self.current_parsing_level + step)
            if self.current_parsing_level == IndentLevel.PredicateMeta.value:
                # finish sub property parsing, clear the field in session
                self.save_register(RegisterUnit.SubProperty, None)
            elif self.current_parsing_level == IndentLevel.Predicate.value:
                # finish predicate parsing, clear the fields in session
                if self.parsing_register[RegisterUnit.Property] is not None:
                    self.save_register(
                        RegisterUnit.Property,
                        Property(name="_", object_type_name="Thing"),
                    )
                elif self.parsing_register[RegisterUnit.Relation] is not None:
                    self.save_register(
                        RegisterUnit.Relation,
                        Relation(name="_", object_type_name="Thing"),
                    )
        elif step == 1:
            assert self.current_parsing_level + 1 < len(IndentLevel), self.error_msg(
                "Invalid indentation (too many levels?)"
            )

            self.current_parsing_level += 1

    def error_msg(self, msg):
        return f"Line# {self.current_line_num}: {msg} (Please refer https://spg.openkg.cn/tutorial/schema/dsl for details)"

    def get_type_name_with_ns(self, type_name: str):
        if "." in type_name:
            return type_name
        else:
            return f"{self.namespace}.{type_name}"

    def parse_type(self, expression):
        """
        parse the SPG type definition
        """

        namespace_match = re.match(r"^namespace\s+([a-zA-Z0-9]+)$", expression)
        if namespace_match:
            assert self.namespace is None, self.error_msg(
                "Duplicated namespace define, please ensure define it only once"
            )

            self.namespace = namespace_match.group(1)
            return

        type_match = re.match(
            r"^([a-zA-Z0-9\.]+)\((\w+)\):\s*?([a-zA-Z0-9,]+)$", expression
        )
        if type_match:
            assert self.namespace is not None, self.error_msg(
                "Missing namespace, please define namespace at the first"
            )

            type_name = type_match.group(1)
            type_name_zh = type_match.group(2).strip()
            type_class = type_match.group(3).strip()
            assert type_class in self.keyword_type, self.error_msg(
                f"{type_class} is illegal, please define it before current line"
            )
            assert (
                type_name.startswith("STD.")
                or "." not in type_name
                or type_name.startswith(f"{self.namespace}.")
            ), self.error_msg(
                f"The name space of {type_name} does not belong to current project."
            )

            spg_type = None
            if type_class == "EntityType":
                spg_type = EntityType(
                    name=self.get_type_name_with_ns(type_name), name_zh=type_name_zh
                )
            elif type_class == "ConceptType":
                spg_type = ConceptType(
                    name=self.get_type_name_with_ns(type_name),
                    name_zh=type_name_zh,
                    hypernym_predicate=HypernymPredicateEnum.IsA,
                )
            elif type_class == "EventType":
                spg_type = EventType(
                    name=self.get_type_name_with_ns(type_name), name_zh=type_name_zh
                )
            elif type_class == "StandardType":
                spg_type = StandardType(name=f"{type_name}", name_zh=type_name_zh)
                spg_type.spreadable = False
                assert type_name.startswith("STD."), self.error_msg(
                    "The name of standard type must start with STD."
                )
            elif type_class == "BasicType" and type_name == "Text":
                spg_type = BasicType.Text
            elif type_class == "BasicType" and type_name == "Integer":
                spg_type = BasicType.Integer
            elif type_class == "BasicType" and type_name == "Float":
                spg_type = BasicType.Float
            ns_type_name = self.get_type_name_with_ns(type_name)
            assert ns_type_name not in self.types, self.error_msg(
                f'Type "{type_name}" is duplicated in the schema'
            )

            self.types[ns_type_name] = spg_type
            self.save_register(RegisterUnit.Type, spg_type)
            return

        sub_type_match = re.match(
            r"^([a-zA-Z0-9]+)\((\w+)\)\s*?->\s*?([a-zA-Z0-9\.]+):$", expression
        )
        if sub_type_match:
            assert self.namespace is not None, self.error_msg(
                "Missing namespace, please define namespace at the first"
            )

            type_name = sub_type_match.group(1)
            type_name_zh = sub_type_match.group(2).strip()
            type_class = sub_type_match.group(3).strip()
            if "." not in type_class:
                ns_type_class = self.get_type_name_with_ns(type_class)
            else:
                ns_type_class = type_class
            assert (
                type_class not in self.keyword_type
                and type_class not in self.internal_type
            ), self.error_msg(f"{type_class} is not a valid inheritable type")
            assert ns_type_class in self.types, self.error_msg(
                f"{type_class} not found, please define it first"
            )

            parent_spg_type = self.types[ns_type_class]
            assert parent_spg_type.spg_type_enum in [
                SpgTypeEnum.Entity,
                SpgTypeEnum.Event,
            ], self.error_msg(
                f'"{type_class}" cannot be inherited, only entity/event type can be inherited.'
            )

            spg_type = EntityType(
                name=f"{self.namespace}.{type_name}", name_zh=type_name_zh
            )
            if parent_spg_type.spg_type_enum == SpgTypeEnum.Event:
                spg_type = EventType(
                    name=f"{self.namespace}.{type_name}", name_zh=type_name_zh
                )
            spg_type.name = type_name
            spg_type.name_zh = type_name_zh
            spg_type.parent_type_name = ns_type_class
            ns_type_name = f"{self.namespace}.{type_name}"
            self.types[ns_type_name] = spg_type
            self.save_register(RegisterUnit.Type, spg_type)
            return

        raise Exception(
            self.error_msg(
                "unrecognized expression, expect namespace A or A(B):C or A(B)->C"
            )
        )

    def parse_type_meta(self, expression):
        """
        parse the meta definition of SPG type
        """

        match = re.match(
            r"^(desc|properties|relations|hypernymPredicate|regular|spreadable|autoRelate):\s*?(.*)$",
            expression,
        )
        assert match, self.error_msg(
            "Unrecognized expression, expect desc:|properties:|relations:"
        )

        type_meta = match.group(1)
        meta_value = match.group(2).strip()

        if type_meta == "desc" and len(meta_value) > 0:
            self.parsing_register[RegisterUnit.Type].desc = meta_value

        elif type_meta == "properties":
            assert self.parsing_register[RegisterUnit.Type].spg_type_enum not in [
                SpgTypeEnum.Standard,
                SpgTypeEnum.Concept,
            ], self.error_msg(
                "Standard/concept type does not allow defining properties."
            )
            self.save_register(
                RegisterUnit.Property, Property(name="_", object_type_name="Thing")
            )

        elif type_meta == "relations":
            assert self.parsing_register[RegisterUnit.Type].spg_type_enum not in [
                SpgTypeEnum.Standard
            ], self.error_msg("Standard type does not allow defining relations.")
            self.save_register(
                RegisterUnit.Relation, Relation(name="_", object_type_name="Thing")
            )

        elif type_meta == "hypernymPredicate":
            assert meta_value in ["isA", "locateAt", "mannerOf"], self.error_msg(
                "Invalid hypernym predicate, expect isA or locateAt or mannerOf"
            )
            assert (
                self.parsing_register[RegisterUnit.Type].spg_type_enum
                == SpgTypeEnum.Concept
            ), self.error_msg("Hypernym predicate is available for concept type only")

            if meta_value == "isA":
                self.parsing_register[
                    RegisterUnit.Type
                ].hypernym_predicate = HypernymPredicateEnum.IsA
            elif meta_value == "locateAt":
                self.parsing_register[
                    RegisterUnit.Type
                ].hypernym_predicate = HypernymPredicateEnum.LocateAt
            elif meta_value == "mannerOf":
                self.parsing_register[
                    RegisterUnit.Type
                ].hypernym_predicate = HypernymPredicateEnum.MannerOf

        elif type_meta == "regular":
            assert (
                self.parsing_register[RegisterUnit.Type].spg_type_enum
                == SpgTypeEnum.Standard
            ), self.error_msg("Regular is available for standard type only")
            self.parsing_register[RegisterUnit.Type].constraint = {
                "REGULAR": meta_value
            }

        elif type_meta == "spreadable":
            assert (
                self.parsing_register[RegisterUnit.Type].spg_type_enum
                == SpgTypeEnum.Standard
            ), self.error_msg("Spreadable is available for standard type only")
            assert meta_value == "True" or meta_value == "False", self.error_msg(
                "Spreadable only accept True or False as its value"
            )
            self.parsing_register[RegisterUnit.Type].spreadable = meta_value == "True"

        elif type_meta == "autoRelate":
            assert (
                self.parsing_register[RegisterUnit.Type].spg_type_enum
                == SpgTypeEnum.Concept
            ), self.error_msg(
                "AutoRelate definition is available for concept type only"
            )
            concept_types = meta_value.split(",")
            for concept in concept_types:
                c = self.get_type_name_with_ns(concept.strip())
                assert (
                    c in self.types
                    and self.types[c].spg_type_enum == SpgTypeEnum.Concept
                ), self.error_msg(
                    f"{concept.strip()} is not a concept type, "
                    f"concept type only allow relationships defined between concept types"
                )
                for k in self.semantic_rel:
                    if k == "IND":
                        continue
                    for p in self.semantic_rel[k]:
                        predicate = Relation(
                            name=p, name_zh=self.semantic_rel_zh[p], object_type_name=c
                        )
                        self.parsing_register[RegisterUnit.Type].add_relation(predicate)
        return

    def check_semantic_relation(self, predicate_name, predicate_class):
        """
        Check if the definition of semantic relations is correct
        """

        name_arr = predicate_name.split("#")
        short_name = name_arr[0]
        pred_name = name_arr[1]
        assert short_name in self.semantic_rel, self.error_msg(
            f"{short_name} is incorrect, expect SYNANT/CAU/SEQ/IND/INC"
        )
        assert pred_name in self.semantic_rel[short_name], self.error_msg(
            f'{pred_name} is incorrect, expect {" / ".join(self.semantic_rel[short_name])}'
        )

        subject_type = self.parsing_register[RegisterUnit.Type]
        predicate_class_ns = predicate_class
        if "." not in predicate_class:
            predicate_class_ns = f"{self.namespace}.{predicate_class}"
        assert (
            predicate_class_ns in self.types or predicate_class_ns in self.defined_types
        ), self.error_msg(
            f"{predicate_class} is illegal, please ensure that it appears in this schema."
        )
        object_type = self.types[predicate_class_ns]

        if short_name == "SYNANT":
            assert subject_type.spg_type_enum == SpgTypeEnum.Concept, self.error_msg(
                "Only concept types could define synonym/antonym relation"
            )
            assert object_type.spg_type_enum == SpgTypeEnum.Concept, self.error_msg(
                "Synonymy/antonym relation can only point to concept types"
            )
        elif short_name == "CAU":
            assert subject_type.spg_type_enum in [
                SpgTypeEnum.Concept,
                SpgTypeEnum.Event,
            ], self.error_msg("Only concept/event types could define causal relation")
            assert object_type.spg_type_enum in [
                SpgTypeEnum.Concept,
                SpgTypeEnum.Event,
            ], self.error_msg(
                f'"{predicate_class}" must be a concept type to conform to the definition of causal relation'
            )
            if subject_type.spg_type_enum == SpgTypeEnum.Concept:
                assert object_type.spg_type_enum == SpgTypeEnum.Concept, self.error_msg(
                    "The causal relation of concept types can only point to concept types"
                )
        elif short_name == "SEQ":
            assert subject_type.spg_type_enum in [
                SpgTypeEnum.Event,
                SpgTypeEnum.Concept,
            ], self.error_msg(
                "Only concept/event types could define sequential relation"
            )
            assert (
                subject_type.spg_type_enum == object_type.spg_type_enum
            ), self.error_msg(
                f'"{predicate_class}" should keep the same type with "{subject_type.name.split(".")[1]}"'
            )
        elif short_name == "IND":
            assert subject_type.spg_type_enum in [
                SpgTypeEnum.Entity,
                SpgTypeEnum.Event,
            ], self.error_msg("Only entity/event types could define inductive relation")
            assert object_type.spg_type_enum == SpgTypeEnum.Concept, self.error_msg(
                f'"{predicate_class}" must be a concept type to conform to the definition of inductive relation'
            )
        elif short_name == "INC":
            assert subject_type.spg_type_enum == SpgTypeEnum.Concept, self.error_msg(
                "Only concept types could define inclusive relation"
            )
            assert object_type.spg_type_enum == SpgTypeEnum.Concept, self.error_msg(
                "The inclusion relation of concept types can only point to concept types"
            )
        elif short_name == "USE":
            assert subject_type.spg_type_enum == SpgTypeEnum.Concept, self.error_msg(
                "Only concept types could define usage relation"
            )
            assert object_type.spg_type_enum == SpgTypeEnum.Concept, self.error_msg(
                "The usage relation of concept types can only point to concept types"
            )

    def parse_predicate(self, expression):
        """
        parse the property/relation definition of SPG type
        """

        match = re.match(
            r"^([a-zA-Z0-9#]+)\(([\w\.]+)\):\s*?([a-zA-Z0-9,\.]+)$", expression
        )
        assert match, self.error_msg(
            "Unrecognized expression, expect pattern like english(Chinese):Type"
        )

        predicate_name = match.group(1)
        predicate_name_zh = match.group(2).strip()
        predicate_class = match.group(3).strip()
        cur_type = self.parsing_register[RegisterUnit.Type]
        type_name = cur_type.name

        if (
            cur_type.spg_type_enum == SpgTypeEnum.Concept
            and self.parsing_register[RegisterUnit.Relation] is None
        ):
            assert "#" in predicate_name, self.error_msg(
                "Concept type only accept following categories of relation: INC#/CAU#/SYNANT#/IND#/USE#/SEQ#"
            )

        if "#" in predicate_name:
            self.check_semantic_relation(predicate_name, predicate_class)
            predicate_name = predicate_name.split("#")[1]
        else:
            for semantic_short in self.semantic_rel.values():
                assert predicate_name not in semantic_short, self.error_msg(
                    f"{predicate_name} is a semantic predicate, please add the semantic prefix"
                )

        if (
            "." in predicate_class
            and predicate_class not in self.types
            and predicate_class not in self.internal_type
        ):
            try:
                cross_type = self.schema.query_spg_type(
                    self.get_type_name_with_ns(predicate_class)
                )
                self.types[self.get_type_name_with_ns(predicate_class)] = cross_type
            except Exception as e:
                raise ValueError(
                    self.error_msg(
                        f"{predicate_class} is illegal, please ensure the name space or type name is correct."
                    )
                )

        assert (
            self.get_type_name_with_ns(predicate_class) in self.types
            or predicate_class in self.internal_type
            or predicate_class in self.defined_types
        ), self.error_msg(
            f"{predicate_class} is illegal, please ensure that it appears in this schema."
        )

        # assert predicate_name not in self.entity_internal_property, self.error_msg(
        #     f"property {predicate_name} is the default property of type"
        # )
        if predicate_class not in self.internal_type:
            spg_type_enum = SpgTypeEnum.Entity
            if self.get_type_name_with_ns(predicate_class) in self.types:
                predicate_type = self.types[self.get_type_name_with_ns(predicate_class)]
                spg_type_enum = predicate_type.spg_type_enum
            elif predicate_class in self.defined_types:
                spg_type_enum_txt = self.defined_types[predicate_class]
                if spg_type_enum_txt == "EntityType":
                    spg_type_enum = SpgTypeEnum.Entity
                elif spg_type_enum_txt == "ConceptType":
                    spg_type_enum = SpgTypeEnum.Concept
                elif spg_type_enum_txt == "EventType":
                    spg_type_enum = SpgTypeEnum.Event
                elif spg_type_enum_txt == "StandardType":
                    spg_type_enum = SpgTypeEnum.Standard

            if cur_type.spg_type_enum == SpgTypeEnum.Concept:
                assert spg_type_enum == SpgTypeEnum.Concept, self.error_msg(
                    "Concept type only allow relationships that point to themselves"
                )
            elif cur_type.spg_type_enum == SpgTypeEnum.Entity:
                assert spg_type_enum != SpgTypeEnum.Event, self.error_msg(
                    "Relationships of entity types are not allowed to point to event types; "
                    "instead, they are only permitted to point from event types to entity types, "
                    "adhering to the principle of moving from dynamic to static."
                )

        if self.parsing_register[RegisterUnit.Relation] is not None:
            assert (
                predicate_name
                not in self.parsing_register[RegisterUnit.Relation].sub_properties
            ), self.error_msg(
                f'Property "{predicate_name}" is duplicated under the relation '
                f"{self.parsing_register[RegisterUnit.Relation].name}"
            )
        else:
            assert (
                predicate_name
                not in self.parsing_register[RegisterUnit.Type].properties
            ), self.error_msg(
                f'Property "{predicate_name}" is duplicated under the type {type_name[type_name.index(".") + 1:]}'
            )
        if predicate_class == "ConceptType":
            assert not self.is_internal_property(
                predicate_name, SpgTypeEnum.Concept
            ), self.error_msg(
                f"property {predicate_name} is the default property of ConceptType"
            )
        if predicate_class == "EventType":
            assert not self.is_internal_property(
                predicate_name, SpgTypeEnum.Event
            ), self.error_msg(
                f"property {predicate_name} is the default property of EventType"
            )

        if (
            "." not in predicate_class
            and predicate_class not in BasicTypeEnum.__members__
        ):
            predicate_class = f"{self.namespace}.{predicate_class}"

        if self.parsing_register[RegisterUnit.SubProperty]:
            # predicate is sub property
            predicate = Property(
                name=predicate_name,
                name_zh=predicate_name_zh,
                object_type_name=predicate_class,
            )
            if self.parsing_register[RegisterUnit.Property] is not None:
                self.parsing_register[RegisterUnit.Property].add_sub_property(predicate)
            elif self.parsing_register[RegisterUnit.Relation] is not None:
                self.parsing_register[RegisterUnit.Relation].add_sub_property(predicate)
            self.save_register(RegisterUnit.SubProperty, predicate)

        elif self.parsing_register[RegisterUnit.Property]:
            # predicate is property
            predicate = Property(
                name=predicate_name,
                name_zh=predicate_name_zh,
                object_type_name=predicate_class,
            )
            if predicate_class in self.types:
                predicate.object_spg_type = self.types[predicate_class].spg_type_enum
                predicate.object_type_name_zh = self.types[predicate_class].name_zh
            if (
                self.parsing_register[RegisterUnit.Type].spg_type_enum
                == SpgTypeEnum.Event
                and predicate_name == "subject"
            ):
                assert predicate_class not in self.internal_type, self.error_msg(
                    f"The subject of event type only allows entity/concept type"
                )

                predicate.property_group = PropertyGroupEnum.Subject
                if "," in predicate_class:
                    # multi-types for subject
                    predicate.object_type_name = "Text"
                    subject_types = predicate_class.split(",")
                    for subject_type in subject_types:
                        subject_type = subject_type.strip()
                        assert (
                            subject_type not in BasicTypeEnum.__members__
                        ), self.error_msg(
                            f"{predicate_class} is illegal for subject in event type"
                        )

                        if "." not in subject_type:
                            subject_type = f"{self.namespace}.{predicate_class}"
                        assert (
                            subject_type in self.types
                            or predicate_class in self.defined_types
                        ), self.error_msg(
                            f"{predicate_class} is illegal, please ensure that it appears in this schema."
                        )

                        subject_predicate = Property(
                            name=f"subject{subject_type}",
                            name_zh=predicate_name_zh,
                            object_type_name=subject_type,
                        )
                        subject_predicate.property_group = PropertyGroupEnum.Subject
                        self.parsing_register[RegisterUnit.Type].add_property(
                            subject_predicate
                        )

            self.parsing_register[RegisterUnit.Type].add_property(predicate)
            self.save_register(RegisterUnit.Property, predicate)

        else:
            # predicate is relation
            assert not predicate_class.startswith("STD."), self.error_msg(
                f"{predicate_class} is not allow appear in the definition of relation."
            )
            assert (
                predicate_class in self.types
                or predicate_class.split(".")[1] in self.defined_types
            ), self.error_msg(
                f"{predicate_class} is illegal, please ensure that it appears in this schema."
            )
            assert (
                f"{predicate_name}_{predicate_class}"
                not in self.parsing_register[RegisterUnit.Type].relations
            ), self.error_msg(
                f'Relation "{match.group()}" is duplicated under the type {type_name[type_name.index(".") + 1:]}'
                if self.parsing_register[RegisterUnit.Type].spg_type_enum
                != SpgTypeEnum.Concept
                else f'Relation "{match.group()}" is already defined by keyword autoRelate'
                f'under the {type_name[type_name.index(".") + 1:]}'
            )

            predicate = Relation(name=predicate_name, object_type_name=predicate_class)
            if predicate_class in self.types:
                predicate.object_spg_type = self.types[predicate_class].spg_type_enum
                predicate.object_type_name_zh = self.types[predicate_class].name_zh
            self.parsing_register[RegisterUnit.Type].add_relation(predicate)
            self.save_register(RegisterUnit.Relation, predicate)
        predicate.name_zh = predicate_name_zh

    def parse_property_meta(self, expression):
        """
        parse the property meta definition of SPG type
        """

        match = re.match(
            r"^(desc|properties|constraint|rule|index):\s*?(.*)$", expression
        )
        assert match, self.error_msg(
            "Unrecognized expression, expect desc:|properties:|constraint:|rule:|index:"
        )

        property_meta = match.group(1)
        meta_value = match.group(2)

        if property_meta == "desc" and len(meta_value) > 0:
            if self.parsing_register[RegisterUnit.SubProperty] is not None:
                self.parsing_register[
                    RegisterUnit.SubProperty
                ].desc = meta_value.strip()
            elif self.parsing_register[RegisterUnit.Property] is not None:
                self.parsing_register[RegisterUnit.Property].desc = meta_value.strip()

        elif property_meta == "constraint":
            if self.parsing_register[RegisterUnit.SubProperty] is not None:
                self.parse_constraint_for_property(
                    meta_value, self.parsing_register[RegisterUnit.SubProperty]
                )
            elif self.parsing_register[RegisterUnit.Property] is not None:
                self.parse_constraint_for_property(
                    meta_value, self.parsing_register[RegisterUnit.Property]
                )
        elif property_meta == "index":
            if self.parsing_register[RegisterUnit.SubProperty] is not None:
                self.parse_index_for_property(
                    meta_value, self.parsing_register[RegisterUnit.SubProperty]
                )
            elif self.parsing_register[RegisterUnit.Property] is not None:
                self.parse_index_for_property(
                    meta_value, self.parsing_register[RegisterUnit.Property]
                )

        elif property_meta == "properties":
            self.save_register(
                RegisterUnit.SubProperty, Property(name="_", object_type_name="Thing")
            )

        elif property_meta == "rule":
            self.parse_predicate_rule(meta_value.lstrip(), RegisterUnit.Property)

    def parse_relation_meta(self, expression):
        """
        parse the relation meta definition of SPG type
        """

        match = re.match(r"^(desc|properties|rule):\s*?(.*)$", expression)
        assert match, self.error_msg(
            "Unrecognized expression, expect desc:|properties:|rule:"
        )

        property_meta = match.group(1)
        meta_value = match.group(2)

        if property_meta == "desc" and len(meta_value) > 0:
            self.parsing_register[RegisterUnit.Relation].desc = meta_value.strip()

        elif property_meta == "properties":
            self.save_register(
                RegisterUnit.SubProperty, Property(name="_", object_type_name="Thing")
            )

        elif property_meta == "rule":
            self.parse_predicate_rule(meta_value.lstrip(), RegisterUnit.Relation)

    def parsing_dispatch(self, expression, parsing_level):
        if parsing_level == IndentLevel.Type.value:
            self.parse_type(expression)

        elif parsing_level == IndentLevel.TypeMeta.value:
            self.parse_type_meta(expression)

        elif parsing_level == IndentLevel.Predicate.value:
            self.parse_predicate(expression)

        elif parsing_level == IndentLevel.PredicateMeta.value:
            if self.parsing_register[RegisterUnit.Property] is not None:
                self.parse_property_meta(expression)

            else:
                self.parse_relation_meta(expression)

        elif parsing_level == IndentLevel.SubProperty.value:
            self.parse_predicate(expression)

        elif parsing_level == IndentLevel.SubPropertyMeta.value:
            self.parse_property_meta(expression)

    def parse_predicate_rule(self, rule, key):
        """
        parse the logic rule for property/relation
        """

        strip_rule = rule
        if strip_rule.startswith("[["):
            self.rule_quote_predicate = self.parsing_register[key]
            self.rule_quote_open = True
            if len(strip_rule) > 2:
                self.rule_quote_predicate.logical_rule = strip_rule[2].lstrip()
            else:
                self.rule_quote_predicate.logical_rule = ""
        else:
            self.parsing_register[key].logical_rule = rule

    def parse_constraint_for_property(self, expression, prop):
        """
        parse the constraint definition of property
        """

        if len(expression) == 0:
            return

        pattern = re.compile(r"(Enum|Regular)\s*?=\s*?\"([^\"]+)\"", re.IGNORECASE)
        matches = re.findall(pattern, expression)
        if matches:
            for group in matches:
                if group[0].lower() == "enum":
                    enum_values = group[1].split(",")
                    strip_enum_values = list()
                    for ev in enum_values:
                        strip_enum_values.append(ev.strip())
                    prop.add_constraint(ConstraintTypeEnum.Enum, strip_enum_values)

                elif group[0].lower() == "regular":
                    prop.add_constraint(ConstraintTypeEnum.Regular, group[1])

        expression = re.sub(r"(Enum|Regular)\s*?=\s*?\"([^\"]+)\"", "", expression)
        array = expression.split(",")
        for cons in array:
            cons = cons.strip()
            if cons.lower() == "multivalue":
                prop.add_constraint(ConstraintTypeEnum.MultiValue)

            elif cons.lower() == "notnull":
                prop.add_constraint(ConstraintTypeEnum.NotNull)

    def parse_index_for_property(self, expression, prop):
        """
        parse the index definition of property
        """

        if len(expression) == 0:
            return

        array = expression.split(",")
        for cons in array:
            cons = cons.strip()
            if cons.lower() == "text":
                prop.index_type = IndexTypeEnum.Text

            elif cons.lower() == "vector":
                prop.index_type = IndexTypeEnum.Vector

            elif cons.lower() == "textandvector":
                prop.index_type = IndexTypeEnum.TextAndVector

    def complete_rule(self, rule):
        """
        Auto generate define statement and append namespace to the entity name
        """

        pattern = re.compile(r"Define\s*\(", re.IGNORECASE)
        match = pattern.match(rule.strip())
        if not match:
            subject_name = self.parsing_register[RegisterUnit.Type].name
            predicate = None
            if self.parsing_register[RegisterUnit.Property] is not None:
                predicate = self.parsing_register[RegisterUnit.Property]
            elif self.parsing_register[RegisterUnit.Relation] is not None:
                predicate = self.parsing_register[RegisterUnit.Relation]
            head = (
                f"Define (s:{subject_name})-[p:{predicate.name}]->(o:{predicate.object_type_name})"
                + " {\n"
            )
            rule = head + rule
            rule += "\n}"

        pattern = re.compile(r"\(([\w\s]*?:)(`?[\w\s\.]+)`?/?[^)]*?\)", re.IGNORECASE)
        matches = re.findall(pattern, rule)
        replace_list = []
        if matches:
            for group in matches:
                if "." in group[1] or group[1].lower() in ["integer", "text", "float"]:
                    continue
                replace_list.append(
                    (
                        f"({group[0]}{group[1]}",
                        f"({group[0]}{self.namespace}.{group[1].strip()}"
                        if "`" not in group[1]
                        else f"({group[0]}`{self.namespace}.{group[1].replace('`', '').strip()}",
                    )
                )
        if len(replace_list) > 0:
            for t in replace_list:
                rule = rule.replace(t[0], t[1])

        return rule.strip()

    def preload_types(self, lines: list):
        """
        Pre analyze the script to obtain defined types
        """

        for line in lines:
            type_match = re.match(
                r"^([a-zA-Z0-9\.]+)\((\w+)\):\s*?([a-zA-Z0-9,]+)$", line
            )
            if type_match:
                self.defined_types[type_match.group(1)] = type_match.group(3).strip()
                continue
            sub_type_match = re.match(
                r"^([a-zA-Z0-9]+)\((\w+)\)\s*?->\s*?([a-zA-Z0-9\.]+):$", line
            )
            if sub_type_match:
                self.defined_types[sub_type_match.group(1)] = sub_type_match.group(
                    3
                ).strip()

    def load_script(self):
        """
        Load and then parse the script file
        """

        file = open(self.schema_file, "r", encoding="utf-8")
        lines = file.read().splitlines()
        self.preload_types(lines)
        for line in lines:
            self.current_line_num += 1
            strip_line = line.strip()
            # replace tabs with two spaces
            line = line.replace("\t", "  ")
            if strip_line == "" or strip_line.startswith("#"):
                # skip empty or comments line
                continue

            if self.rule_quote_open:
                # process the multi-line assignment [[ .... ]]
                right_strip_line = line.rstrip()
                if strip_line.endswith("]]"):
                    self.rule_quote_open = False
                    if len(right_strip_line) > 2:
                        self.rule_quote_predicate.logical_rule += right_strip_line[
                            : len(right_strip_line) - 2
                        ]
                    self.rule_quote_predicate.logical_rule = self.complete_rule(
                        self.rule_quote_predicate.logical_rule
                    )

                else:
                    self.rule_quote_predicate.logical_rule += line + "\n"
                continue

            indent_count = len(line) - len(line.lstrip())
            if indent_count == 0:
                # the line without indent is namespace definition or a type definition
                self.adjust_parsing_level(0)

            elif indent_count > self.last_indent_level:
                # the line is the sub definition of the previous line
                self.adjust_parsing_level(1)

            elif indent_count < self.last_indent_level:
                # finish current indent parsing
                backward_step = None
                for i in range(0, len(self.indent_level_pos)):
                    if indent_count == self.indent_level_pos[i]:
                        backward_step = i - self.current_parsing_level
                        break
                assert backward_step, self.error_msg(
                    f"Invalid indentation, please align with the previous definition"
                )

                if backward_step != 0:
                    self.adjust_parsing_level(backward_step)

            self.parsing_dispatch(strip_line, self.current_parsing_level)
            self.last_indent_level = indent_count
            self.indent_level_pos[self.current_parsing_level] = indent_count

    def is_internal_property(self, prop: Property, spg_type: SpgTypeEnum):
        if spg_type == SpgTypeEnum.Entity or spg_type == SpgTypeEnum.Standard:
            return prop in self.entity_internal_property

        elif spg_type == SpgTypeEnum.Concept:
            return prop in self.concept_internal_property

        elif spg_type == SpgTypeEnum.Event:
            return prop in self.event_internal_property

    def sync_schema(self):
        return self.diff_and_sync(False)

    def print_diff(self):
        self.diff_and_sync(True)

    def diff_sub_property(self, new, old, old_type_name, old_property, new_property):
        need_update = False
        inherited_type = self.get_inherited_type(old_type_name)
        for prop in old:
            if not old_property.inherited and prop not in new:
                assert inherited_type is None, self.error_msg(
                    f'"{old_type_name} was inherited by other type, such as "{inherited_type}". Prohibit property alteration!'
                )

                old[prop].alter_operation = AlterOperationEnum.Delete
                need_update = True
                print(
                    f"Delete sub property: [{old_type_name}] {old_property.name}.{prop}"
                )

        for prop, o in new.items():
            if prop not in old and not new_property.inherited:
                assert inherited_type is None, self.error_msg(
                    f'"{old_type_name} was inherited by other type, such as "{inherited_type}". Prohibit property alteration!'
                )

                old_property.add_sub_property(new[prop])
                need_update = True
                print(
                    f"Create sub property: [{old_type_name}] {old_property.name}.{prop}"
                )

            elif old[prop].object_type_name != new[prop].object_type_name:
                assert inherited_type is None, self.error_msg(
                    f'"{old_type_name} was inherited by other type, such as "{inherited_type}". Prohibit property alteration!'
                )
                assert not old_property.inherited, self.error_msg(
                    f"{old_type_name}] {old_property.name}.{prop} is inherited sub property, deny modify"
                )

                old[prop].alter_operation = AlterOperationEnum.Delete
                old_property.add_sub_property(new[prop])
                need_update = True
                print(
                    f"Recreate sub property: [{old_type_name}] {old_property.name}.{prop}"
                )

            elif old[prop] != new[prop]:
                assert inherited_type is None, self.error_msg(
                    f'"{old_type_name} was inherited by other type, such as "{inherited_type}". Prohibit property alteration!'
                )
                assert not old_property.inherited, self.error_msg(
                    f"{old_type_name}] {old_property.name}.{prop} is inherited property, deny modify"
                )

                old[prop].overwritten_by(o)
                old[prop].alter_operation = AlterOperationEnum.Update
                need_update = True
                print(f"Update property: [{old_type_name}] {old_property.name}.{prop}")
        return need_update

    def get_inherited_type(self, type_name):
        for spg_type in self.types:
            if self.types[spg_type].parent_type_name == type_name:
                return spg_type
        return None

    def diff_and_sync(self, print_only):
        """
        Get the schema diff and then sync to graph storage
        """
        session = self.schema.create_session()

        # generate the delete list of spg type
        for spg_type in session.spg_types:
            if not spg_type.startswith("STD.") and not spg_type.startswith(
                f"{self.namespace}."
            ):
                continue
            unique_id = session.spg_types[spg_type]._rest_model.ontology_id.unique_id
            if spg_type in self.internal_type and unique_id < 1000:
                continue

            if spg_type not in self.types:
                session.delete_type(session.get(spg_type))
                print(f"Delete type: {spg_type}")

        for spg_type in self.types:
            # generate the creation list of spg type
            if not spg_type.startswith("STD.") and not spg_type.startswith(
                f"{self.namespace}."
            ):
                continue
            if spg_type not in session.spg_types:
                session.create_type(self.types[spg_type])
                print(f"Create type: {spg_type}")
                relations = self.types[spg_type].relations
                if len(relations) > 0:
                    for rel in relations:
                        print(f'Create relation: [{spg_type}] {rel.split("_")[0]}')

            else:
                # generate the update list
                new_type = self.types[spg_type]
                old_type = session.get(spg_type)

                assert (
                    new_type.spg_type_enum == old_type.spg_type_enum
                    and new_type.parent_type_name == old_type.parent_type_name
                ), self.error_msg(
                    f"Cannot alter the type definition or its parent type of {new_type.name}. "
                    "if you still want to make change, please delete it first then re-create it."
                )

                need_update = False
                if new_type.desc != old_type.desc:
                    old_type.desc = new_type.desc
                    need_update = True

                if new_type.name_zh != old_type.name_zh:
                    old_type.name_zh = new_type.name_zh
                    need_update = True

                if new_type.spg_type_enum == SpgTypeEnum.Concept:
                    assert (
                        new_type.hypernym_predicate == old_type.hypernym_predicate
                    ), self.error_msg(
                        f"Cannot alter the hypernym predicate of {new_type.name}. "
                        "if you still want to make change, please delete it first then re-create it."
                    )

                if new_type.spg_type_enum == SpgTypeEnum.Standard:
                    assert old_type.spreadable == new_type.spreadable, self.error_msg(
                        f"Cannot alter the spreadable value of {new_type.name}. "
                        f"if you still want to make change, "
                        "please delete the definition first and then re-create it."
                    )

                    if old_type.constraint != new_type.constraint:
                        old_type.constraint = new_type.constraint
                        need_update = True
                        print(f"Update standard type constraint: {spg_type}")

                inherited_type = self.get_inherited_type(new_type.name)
                for prop in old_type.properties:
                    if (
                        not old_type.properties[prop].inherited
                        and prop not in new_type.properties
                        and not self.is_internal_property(prop, new_type.spg_type_enum)
                    ):
                        assert (
                            prop != "subject"
                            and old_type.properties[prop].property_group
                            != PropertyGroupEnum.Subject
                        ), self.error_msg(
                            "The subject property of event type cannot be deleted"
                        )
                        assert inherited_type is None, self.error_msg(
                            f'"{new_type.name} was inherited by other type, such as "{inherited_type}". Prohibit property alteration!'
                        )

                        old_type.properties[
                            prop
                        ].alter_operation = AlterOperationEnum.Delete
                        need_update = True
                        print(f"Delete property: [{new_type.name}] {prop}")

                for prop, o in new_type.properties.items():

                    if (
                        prop not in old_type.properties
                        and not self.is_internal_property(prop, new_type.spg_type_enum)
                        and not o.inherited
                    ):
                        assert inherited_type is None, self.error_msg(
                            f'"{new_type.name} was inherited by other type, such as "{inherited_type}". Prohibit property alteration!'
                        )

                        old_type.add_property(new_type.properties[prop])
                        need_update = True
                        print(f"Create property: [{new_type.name}] {prop}")

                    elif (
                        old_type.properties[prop].object_type_name
                        != new_type.properties[prop].object_type_name
                    ):
                        assert inherited_type is None, self.error_msg(
                            f'"{new_type.name} was inherited by other type, such as "{inherited_type}". Prohibit property alteration!'
                        )
                        assert not old_type.properties[prop].inherited, self.error_msg(
                            f"{new_type.name}] {prop} is inherited property, deny modify"
                        )

                        old_type.properties[
                            prop
                        ].alter_operation = AlterOperationEnum.Delete
                        old_type.add_property(new_type.properties[prop])
                        need_update = True
                        print(f"Recreate property: [{new_type.name}] {prop}")

                    elif (
                        old_type.properties[prop].sub_properties
                        != new_type.properties[prop].sub_properties
                    ):
                        need_update = self.diff_sub_property(
                            new_type.properties[prop].sub_properties,
                            old_type.properties[prop].sub_properties,
                            old_type.name,
                            old_type.properties[prop],
                            new_type.properties[prop],
                        )
                        if need_update:
                            old_type.properties[
                                prop
                            ].alter_operation = AlterOperationEnum.Update

                    elif old_type.properties[prop] != new_type.properties[prop]:
                        assert inherited_type is None, self.error_msg(
                            f'"{new_type.name} was inherited by other type, such as "{inherited_type}". Prohibit property alteration!'
                        )
                        assert not old_type.properties[prop].inherited, self.error_msg(
                            f"{new_type.name}] {prop} is inherited property, deny modify"
                        )

                        old_type.properties[prop].overwritten_by(o)
                        old_type.properties[
                            prop
                        ].alter_operation = AlterOperationEnum.Update
                        need_update = True
                        print(f"Update property: [{new_type.name}] {prop}")

                for relation in new_type.relations:
                    p_name = relation.split("_")[0]
                    if (
                        relation not in old_type.relations
                        or old_type.relations[relation].object_type_name
                        != new_type.relations[relation].object_type_name
                    ):
                        assert inherited_type is None, self.error_msg(
                            f'"{new_type.name} was inherited by other type, such as "{inherited_type}". Prohibit relation alteration!'
                        )
                        old_type.add_relation(new_type.relations[relation])
                        need_update = True
                        print(f"Create relation: [{new_type.name}] {p_name}")

                    elif (
                        old_type.relations[relation].sub_properties
                        != new_type.relations[relation].sub_properties
                    ):
                        need_update = self.diff_sub_property(
                            new_type.relations[relation].sub_properties,
                            old_type.relations[relation].sub_properties,
                            old_type.name,
                            old_type.relations[relation],
                            new_type.relations[relation],
                        )
                        if need_update:
                            assert inherited_type is None, self.error_msg(
                                f'"{new_type.name} was inherited by other type, such as "{inherited_type}". Prohibit relation alteration!'
                            )
                            old_type.relations[
                                relation
                            ].alter_operation = AlterOperationEnum.Update

                    elif old_type.relations[relation] != new_type.relations[relation]:
                        assert inherited_type is None, self.error_msg(
                            f'"{new_type.name} was inherited by other type, such as "{inherited_type}". Prohibit relation alteration!'
                        )
                        assert not old_type.relations[
                            relation
                        ].inherited, self.error_msg(
                            f"{new_type.name}] {p_name} is inherited relation, deny modify"
                        )

                        old_type.relations[relation].overwritten_by(
                            new_type.relations[relation]
                        )
                        old_type.relations[
                            relation
                        ].alter_operation = AlterOperationEnum.Update
                        need_update = True
                        print(f"Update relation: [{new_type.name}] {relation}")

                for relation, o in old_type.relations.items():
                    p_name = relation.split("_")[0]
                    if o.inherited or p_name in new_type.properties or o.is_dynamic:
                        # skip the inherited and semantic relation
                        continue
                    if (
                        relation not in new_type.relations
                        and not o.inherited
                        and not o.is_dynamic
                        and not (
                            new_type.spg_type_enum == SpgTypeEnum.Concept
                            and p_name
                            in [member.value for member in HypernymPredicateEnum]
                        )
                    ):
                        assert inherited_type is None, self.error_msg(
                            f'"{new_type.name} was inherited by other type, such as "{inherited_type}". Prohibit relation alteration!'
                        )
                        old_type.relations[
                            relation
                        ].alter_operation = AlterOperationEnum.Delete
                        need_update = True
                        print(f"Delete relation: [{new_type.name}] {p_name}")

                if need_update:
                    session.update_type(old_type)
        if not print_only:
            session.commit()
        if session._alter_spg_types:
            return True
        return False

    def export_schema_python(self, filename):
        """
        Export the schema helper class in python
        You can import the exported class in your code to obtain the code prompt in IDE
        """

        schema = SchemaClient()
        session = schema.create_session()
        assert len(self.namespace) > 0, "Schema is invalid"

        spg_types = []
        for spg_type_name in sorted(session.spg_types):
            if (
                spg_type_name.startswith("STD.")
                or not spg_type_name.startswith(self.namespace)
                or spg_type_name in self.internal_type
            ):
                continue

            sub_properties = {}
            properties = set()
            for prop, prop_type in session.get(spg_type_name).properties.items():
                if len(prop_type.sub_properties) > 0:
                    sub_properties[prop] = set()
                    for sub_prop in prop_type.sub_properties:
                        sub_properties[prop].add(sub_prop)
                else:
                    properties.add(prop)

            relations = set()
            relation_sub_properties = {}
            hyp_predicate = [member.value for member in HypernymPredicateEnum]
            for relation, relation_type in session.get(spg_type_name).relations.items():
                rel = relation.split("_")[0]
                if (
                    rel in relations
                    or rel in hyp_predicate
                    or rel in session.get(spg_type_name).properties
                ):
                    continue

                if len(relation_type.sub_properties) > 0:
                    relation_sub_properties[rel] = set()
                    for sub_prop in relation_type.sub_properties:
                        relation_sub_properties[rel].add(sub_prop)
                else:
                    relations.add(rel)

            spg_types.append(
                {
                    "name": spg_type_name.split(".")[1],
                    "properties": properties,
                    "sub_properties": sub_properties,
                    "relations": relations,
                    "relation_sub_properties": relation_sub_properties,
                }
            )

        metadata = {"namespace": self.namespace, "spg_types": spg_types}

        from knext.common.utils import render_template

        render_template(Path(filename).parent, Path(filename).name, **metadata)


if __name__ == "__main__":
    os.environ["KAG_PROJECT_ID"] = "4"
    schema = SPGSchemaMarkLang(
        "/Users/jier/Desktop/openspgapp/openspg/python/knext/knext/examples/medicine/schema/medicine.schema"
    )
    schema.diff_and_sync(False)
