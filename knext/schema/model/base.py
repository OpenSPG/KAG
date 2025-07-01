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

import pprint
import typing
from abc import ABC
from enum import Enum
from typing import Type, Union, List, Dict, Optional

from knext.schema import rest

ROOT_TYPE_UNIQUE_NAME = "Thing"


class SpgTypeEnum(str, Enum):
    Basic = "BASIC_TYPE"
    Standard = "STANDARD_TYPE"
    Entity = "ENTITY_TYPE"
    Index = "INDEX_TYPE"
    Event = "EVENT_TYPE"
    Concept = "CONCEPT_TYPE"


class BasicTypeEnum(str, Enum):
    Text = "Text"
    Integer = "Integer"
    Float = "Float"


class PropertyGroupEnum(str, Enum):
    Time = "TIME"
    Subject = "SUBJECT"
    Object = "OBJECT"
    Loc = "LOC"


class ConstraintTypeEnum(str, Enum):
    NotNull = "NOT_NULL"
    MultiValue = "MULTI_VALUE"
    Enum = "ENUM"
    Regular = "REGULAR"


class HypernymPredicateEnum(str, Enum):
    IsA = "isA"
    LocateAt = "locateAt"
    MannerOf = "mannerOf"


class AlterOperationEnum(str, Enum):
    Create = "CREATE"
    Update = "UPDATE"
    Delete = "DELETE"


class IndexTypeEnum(str, Enum):
    Vector = "VECTOR"
    SparseVector = "SPARSE_VECTOR"
    Text = "TEXT"
    TextAndVector = "TEXT_AND_VECTOR"
    TextAndSparseVector = "TEXT_AND_SPARSE_VECTOR"


def iter_init(klass):
    """Initialize a REST model."""
    instance = klass()
    for attr, attr_type in klass.openapi_types.items():
        if hasattr(rest, attr_type):
            attr_klass = getattr(rest, attr_type)
            attr_instance = iter_init(attr_klass)
            setattr(instance, attr, attr_instance)
        elif attr_type.startswith("list["):
            setattr(instance, attr, [])
        else:
            pass

    return instance


class BaseProperty(ABC):
    """Base class of `Property` and `Relation`."""

    _rest_model: Union[rest.Relation, rest.Property]

    def __init__(
        self,
        name=None,
        object_type_name=None,
        name_zh=None,
        desc=None,
        property_group=None,
        sub_properties=None,
        constraint=None,
        logical_rule=None,
        index_type=None,
        **kwargs,
    ):
        if "rest_model" in kwargs:
            self._rest_model = kwargs["rest_model"]
        else:
            self._init_rest_model(
                name=name,
                object_type_name=object_type_name,
                name_zh=name_zh,
                desc=desc,
                property_group=property_group,
                sub_properties=sub_properties,
                constraint=constraint,
                logical_rule=logical_rule,
                index_type=index_type,
            )

    def _init_rest_model(self, **kwargs):
        """Init a BaseProperty object."""
        super_klass = self.__class__.__name__
        self._rest_model = iter_init(getattr(rest, super_klass))
        for param, value in kwargs.items():
            setattr(self, param, value)

    @property
    def name(self) -> str:
        """Gets the name of this Property/Relation.  # noqa: E501


        :return: The name of this Property/Relation.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.basic_info.name.name

    @name.setter
    def name(self, name: str):
        """Sets the name of this Property/Relation.


        :param name: The name of this Property/Relation.  # noqa: E501
        :type: str
        """

        self._rest_model.basic_info.name.name = name

    @property
    def object_type_name(self) -> str:
        """Gets the object_type_name of this Property/Relation.  # noqa: E501


        :return: The object_type_name of this Property/Relation.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.object_type_ref.basic_info.name.name

    @property
    def object_type_name_en(self) -> str:
        """Gets the object_type_name_en of this Property/Relation.  # noqa: E501


        :return: The object_type_name_en of this Property/Relation.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.object_type_ref.basic_info.name.name_en

    @object_type_name_en.setter
    def object_type_name_en(self, object_type_name_en: str):
        """Sets the object_type_name_en of this Property/Relation.


        :param object_type_name_en: The object_type_name_en of this Property/Relation.  # noqa: E501
        :type: str
        """

        self._rest_model.object_type_ref.basic_info.name.name_en = object_type_name_en

    @object_type_name.setter
    def object_type_name(self, object_type_name: str):
        """Sets the object_type_name of this Property/Relation.


        :param object_type_name: The object_type_name of this Property/Relation.  # noqa: E501
        :type: str
        """

        self._rest_model.object_type_ref.basic_info.name.name = object_type_name

    @property
    def object_type_name_zh(self) -> str:
        """Gets the object_type_name_zh of this Property/Relation.  # noqa: E501


        :return: The object_type_name_zh of this Property/Relation.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.object_type_ref.basic_info.name_zh

    @object_type_name_zh.setter
    def object_type_name_zh(self, object_type_name_zh: str):
        """Sets the object_type_name_zh of this Property/Relation.


        :param object_type_name_zh: The object_type_name_zh of this Property/Relation.  # noqa: E501
        :type: str
        """
        self._rest_model.object_type_ref.basic_info.name_zh = object_type_name_zh

    @property
    def inherited(self) -> bool:
        """Gets the `inherited` of this Property/Relation.  # noqa: E501


        :return: The `inherited` of this Property/Relation.  # noqa: E501
        :rtype: bool
        """
        return self._rest_model.inherited

    @inherited.setter
    def inherited(self, inherited: bool):
        """Sets the `inherited` of this Property/Relation.


        :param inherited: The `inherited` of this Property/Relation.  # noqa: E501
        :type: bool
        """

        if inherited is None:
            return

        self._rest_model.inherited = inherited

    @property
    def object_spg_type(self) -> Optional[SpgTypeEnum]:
        """Gets the object_spg_type of this Property/Relation.  # noqa: E501


        :return: The object_spg_type of this Property/Relation.  # noqa: E501
        :rtype: str
        """
        spg_type_enum = self._rest_model.object_type_ref.spg_type_enum
        return SpgTypeEnum(spg_type_enum) if spg_type_enum else None

    @object_spg_type.setter
    def object_spg_type(self, object_spg_type: SpgTypeEnum):
        """Sets the object_spg_type of this Property/Relation.


        :param object_spg_type: The object_spg_type of this Property/Relation.  # noqa: E501
        :type: str
        """

        if object_spg_type is None:
            return

        self._rest_model.object_type_ref.spg_type_enum = object_spg_type

    @property
    def name_zh(self) -> str:
        """Gets the name_zh of this Property/Relation.  # noqa: E501


        :return: The name_zh of this Property/Relation.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.basic_info.name_zh

    @name_zh.setter
    def name_zh(self, name_zh: str):
        """Sets the name_zh of this Property/Relation.


        :param name_zh: The name_zh of this Property/Relation.  # noqa: E501
        :type: str
        """
        if name_zh is None:
            return

        self._rest_model.basic_info.name_zh = name_zh

    @property
    def desc(self) -> str:
        """Gets the desc of this Property/Relation.  # noqa: E501


        :return: The desc of this Property/Relation.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.basic_info.desc

    @desc.setter
    def desc(self, desc: str):
        """Sets the desc of this Property/Relation.


        :param desc: The desc of this Property/Relation.  # noqa: E501
        :type: str
        """
        if desc is None:
            return

        self._rest_model.basic_info.desc = desc

    @property
    def property_group(self) -> Optional[PropertyGroupEnum]:
        """Gets the property_group of this Property/Relation.  # noqa: E501


        :return: The property_group of this Property/Relation.  # noqa: E501
        :rtype: str
        """
        property_group = self._rest_model.advanced_config.property_group
        return PropertyGroupEnum(property_group) if property_group else None

    @property_group.setter
    def property_group(self, property_group: PropertyGroupEnum):
        """Sets the property_group of this Property/Relation.


        :param property_group: The property_group of this Property/Relation.  # noqa: E501
        :type: str
        """
        if property_group is None:
            return

        self._rest_model.advanced_config.property_group = property_group

    @property
    def sub_properties(self) -> Dict[str, Type["Property"]]:
        """Gets the sub_properties of this Property/Relation.  # noqa: E501


        :return: The sub_properties of this Property/Relation.  # noqa: E501
        :rtype: dict
        """
        if self._rest_model.advanced_config.sub_properties is None:
            return {}
        from knext.schema.model.property import Property

        sub_properties = {}
        for sub_property in self._rest_model.advanced_config.sub_properties:
            sub_properties[sub_property.basic_info.name.name] = Property(
                name=sub_property.basic_info.name.name,
                object_type_name=sub_property.object_type_ref.basic_info.name.name,
                rest_model=sub_property,
            )
        return sub_properties

    @sub_properties.setter
    def sub_properties(self, sub_properties: List["Property"]):
        """Sets the sub_properties of this Property/Relation.


        :param sub_properties: The sub_properties of this Property/Relation.  # noqa: E501
        :type: list[Property]
        """

        if sub_properties is None:
            return

        self._rest_model.advanced_config.sub_properties = [
            prop.to_rest() for prop in sub_properties
        ]

    def add_sub_property(self, sub_property: Type["Property"]):
        """Adds a sub_property to this Property/Relation.


        :param sub_property: The sub_property to add.
        :type sub_property: Property
        """

        if self._rest_model.advanced_config.sub_properties is None:
            self._rest_model.advanced_config.sub_properties = None
        sub_property.alter_operation = AlterOperationEnum.Create
        self._rest_model.advanced_config.sub_properties.append(sub_property.to_rest())
        return self

    @property
    def constraint(self) -> Dict[ConstraintTypeEnum, Union[str, list]]:
        """Gets the constraint of this Property.  # noqa: E501


        :return: The constraint of this Property.  # noqa: E501
        :rtype: dict
        """
        if self._rest_model.advanced_config.constraint is None:
            return {}
        constraint = {}
        for item in self._rest_model.advanced_config.constraint.constraint_items:
            if item.constraint_type_enum == ConstraintTypeEnum.Enum:
                value = item.enum_values
            elif item.constraint_type_enum == ConstraintTypeEnum.Regular:
                value = item.regular_pattern
            else:
                value = None
            constraint[item.constraint_type_enum] = value
        return constraint

    @constraint.setter
    def constraint(self, constraint: Dict[ConstraintTypeEnum, Union[str, list]]):
        """Sets the constraint of this Property.


        :param constraint: The constraint of this Property.  # noqa: E501
        :type: dict
        """
        if constraint is None:
            return
        self._rest_model.advanced_config.constraint = rest.Constraint(
            constraint_items=[]
        )
        for type, value in constraint.items():
            self.add_constraint(type, value)

    def add_constraint(self, type: ConstraintTypeEnum, value: Union[str, list] = None):
        """Adds a constraint to this Property.


        :param type: The type of constraint to add.
        :type type: ConstraintTypeEnum
        :param value: The value(s) of the constraint. Optional.
        :type value: str or list, optional
        """

        if self._rest_model.advanced_config.constraint is None:
            self._rest_model.advanced_config.constraint = rest.Constraint(
                constraint_items=[]
            )
        if type == ConstraintTypeEnum.Enum:
            if not isinstance(value, list):
                raise ValueError("Invalid enum format.")
            constraint_item = rest.EnumConstraint(enum_values=value)
        elif type == ConstraintTypeEnum.Regular:
            constraint_item = rest.RegularConstraint(regular_pattern=value)
        else:
            constraint_item = rest.BaseConstraintItem(type)
        self._rest_model.advanced_config.constraint.constraint_items.append(
            constraint_item
        )
        return self

    @property
    def logical_rule(self) -> str:
        """Gets the logical_rule of this Property/Relation.  # noqa: E501


        :return: The logical_rule of this Property/Relation.  # noqa: E501
        :rtype: str
        """
        if self._rest_model.advanced_config.logical_rule is None:
            return ""
        return self._rest_model.advanced_config.logical_rule.content

    @logical_rule.setter
    def logical_rule(self, logical_rule: str):
        """Sets the logical_rule of this Property/Relation.


        :param logical_rule: The logical_rule of this Property/Relation.  # noqa: E501
        :type: str
        """
        if not logical_rule:
            self._rest_model.advanced_config.logical_rule = None
            return
        if self._rest_model.advanced_config.logical_rule is None:
            self._rest_model.advanced_config.logical_rule = rest.LogicalRule()

        self._rest_model.advanced_config.logical_rule.content = logical_rule

    @property
    def index_type(self) -> IndexTypeEnum:
        """Gets the index_type of this Property/Relation.  # noqa: E501


        :return: The index_type of this Property/Relation.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.advanced_config.index_type

    @index_type.setter
    def index_type(self, index_type: IndexTypeEnum):
        """Sets the index_type of this Property/Relation.


        :param index_type: The index_type of this Property/Relation.  # noqa: E501
        :type: str
        """
        if index_type is None:
            return

        self._rest_model.advanced_config.index_type = index_type

    @property
    def alter_operation(self) -> AlterOperationEnum:
        """Gets the alter_operation of this Property/Relation.  # noqa: E501


        :return: The alter_operation of this Property/Relation.  # noqa: E501
        :rtype: AlterOperationEnum
        """
        alter_operation = self._rest_model.alter_operation
        return AlterOperationEnum(alter_operation) if alter_operation else None

    @alter_operation.setter
    def alter_operation(self, alter_operation: AlterOperationEnum):
        """Sets the alter_operation of this Property/Relation.


        :param alter_operation: The alter_operation of this Property/Relation.  # noqa: E501
        :type: AlterOperationEnum
        """
        self._rest_model.alter_operation = alter_operation

    def overwritten_by(self, other: Type["BaseProperty"]):
        """Overwrite all variables of the current class instance from another class instance."""
        import inspect

        members = inspect.getmembers(self.__class__)
        for name, member in members:
            if isinstance(member, property):
                if name == "sub_properties":
                    setattr(
                        self, name, [prop for _, prop in getattr(other, name).items()]
                    )
                else:
                    setattr(self, name, getattr(other, name))

    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in self.__annotations__.items():
            if attr == "sub_properties":
                continue
            value = getattr(self, attr)
            if isinstance(value, typing.List):
                result[attr] = list(
                    map(lambda x: x.to_dict() if hasattr(x, "to_dict") else x, value)
                )
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, typing.Dict):
                result[attr] = dict(
                    map(
                        lambda item: (
                            (item[0], item[1].to_dict())
                            if hasattr(item[1], "to_dict")
                            else item
                        ),
                        value.items(),
                    )
                )
            else:
                result[attr] = value

        return result

    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())

    def to_rest(self):
        """Returns the REST model of this SpgType"""
        return self._rest_model

    def __repr__(self):
        """For `print` and `pprint`"""
        return self.to_str()

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        if not isinstance(other, self.__class__):
            return False

        return self.to_dict() == other.to_dict()

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        if not isinstance(other, self.__class__):
            return True

        return self.to_dict() != other.to_dict()


class BaseSpgType(ABC):
    """Base class of `ConceptType`, `EntityType`, `EventType`, `StandardType`, `BasicType`."""

    _rest_model: Union[
        rest.ConceptType,
        rest.EntityType,
        rest.IndexType,
        rest.EventType,
        rest.StandardType,
    ]

    def __init__(
        self,
        spg_type_enum=None,
        name=None,
        name_zh=None,
        desc=None,
        parent_type_name=None,
        properties=None,
        relations=None,
        **kwargs,
    ):
        if "rest_model" in kwargs:
            self._rest_model = kwargs["rest_model"]
        else:
            self._init_rest_model(
                spg_type_enum=spg_type_enum,
                name=name,
                name_zh=name_zh,
                desc=desc,
                parent_type_name=parent_type_name,
                properties=properties,
                relations=relations,
                **kwargs,
            )

    def _init_rest_model(self, **kwargs):
        """Init a BaseSpgType object."""
        super_klass = self.__class__.__name__
        self._rest_model = iter_init(getattr(rest, super_klass))
        for param, value in kwargs.items():
            setattr(self, param, value)

    @property
    def spg_type_enum(self) -> SpgTypeEnum:
        """Gets the spg_type_enum of this SpgType.  # noqa: E501


        :return: The spg_type_enum of this SpgType.  # noqa: E501
        :rtype: str
        """
        spg_type_enum = self._rest_model.spg_type_enum
        return SpgTypeEnum(spg_type_enum) if spg_type_enum else None

    @spg_type_enum.setter
    def spg_type_enum(self, spg_type_enum: SpgTypeEnum):
        """Sets the spg_type_enum of this SpgType.


        :param spg_type_enum: The spg_type_enum of this SpgType.  # noqa: E501
        :type: str
        """
        self._rest_model.spg_type_enum = spg_type_enum

    @property
    def name(self) -> str:
        """Gets the name of this SpgType.  # noqa: E501


        :return: The name of this SpgType.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.basic_info.name.name

    @property
    def name_en(self) -> str:
        """Gets the name_en of this SpgType.  # noqa: E501


        :return: The name_en of this SpgType.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.basic_info.name.name_en

    @name.setter
    def name(self, name: str):
        """Sets the name of this SpgType.


        :param name: The name of this SpgType.  # noqa: E501
        :type: str
        """
        if name is None:  # noqa: E501
            raise ValueError(
                "Invalid value for `name`, must not be `None`"
            )  # noqa: E501

        if self._rest_model.basic_info.name.name != name:
            self._rest_model.basic_info.name.name = name

    @property
    def name_zh(self) -> str:
        """Gets the name_zh of this SpgType.  # noqa: E501


        :return: The name_zh of this SpgType.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.basic_info.name_zh

    @name_zh.setter
    def name_zh(self, name_zh: str):
        """Sets the name_zh of this SpgType.


        :param name_zh: The name_zh of this SpgType.  # noqa: E501
        :type: str
        """

        if self._rest_model.basic_info.name_zh == name_zh:
            return
        self._rest_model.basic_info.name_zh = name_zh

    @property
    def desc(self) -> str:
        """Gets the desc of this SpgType.  # noqa: E501


        :return: The desc of this SpgType.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.basic_info.desc

    @desc.setter
    def desc(self, desc: str):
        """Sets the desc of this SpgType.


        :param desc: The desc of this SpgType.  # noqa: E501
        :type: str
        """

        self._rest_model.basic_info.desc = desc

    @property
    def parent_type_name(self) -> str:
        """Gets the parent_type_name of this SpgType.  # noqa: E501


        :return: The parent_type_name of this SpgType.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.parent_type_info.parent_type_identifier.name

    @parent_type_name.setter
    def parent_type_name(self, parent_type_name: str):
        """Sets the parent_type_name of this SpgType.


        :param parent_type_name: The parent_type_name of this SpgType.  # noqa: E501
        :type: BaseSpgType
        """
        if parent_type_name is None:
            return
        self._rest_model.parent_type_info.parent_type_identifier.name = parent_type_name

    @property
    def properties(self) -> Dict[str, Type["Property"]]:
        """Gets the properties of this SpgType.  # noqa: E501


        :return: The properties of this SpgType.  # noqa: E501
        :rtype: dict
        """
        from knext.schema.model.property import Property

        properties = {}
        for prop in self._rest_model.properties:
            properties[prop.basic_info.name.name] = Property(
                name=prop.basic_info.name.name,
                object_type_name=prop.object_type_ref.basic_info.name.name,
                rest_model=prop,
            )
        return properties

    @properties.setter
    def properties(self, properties: List[Type["Property"]]):
        """Sets the properties of this SpgType.


        :param properties: The properties of this SpgType.  # noqa: E501
        :type: list[Property]
        """
        if properties is None:
            return

        self._rest_model.properties = [prop.to_rest() for prop in properties]

    def add_property(self, prop: Type["Property"]):
        """Adds a property to this SpgType.


        :param prop: The property to add.  # noqa: E501
        :type: Property
        """
        prop.alter_operation = AlterOperationEnum.Create
        self._rest_model.properties.append(prop.to_rest())
        return self

    @property
    def relations(self) -> Dict[str, Type["Relation"]]:
        """Gets the relations of this SpgType.  # noqa: E501


        :return: The relations of this SpgType.  # noqa: E501
        :rtype: dict
        """
        from knext.schema.model.relation import Relation

        relations = {}
        for relation in self._rest_model.relations:
            predicate_name = relation.basic_info.name.name
            object_type_name = relation.object_type_ref.basic_info.name.name
            relations[predicate_name + "_" + object_type_name] = Relation(
                name=predicate_name,
                object_type_name=object_type_name,
                rest_model=relation,
            )
        return relations

    @relations.setter
    def relations(self, relations: List["Relation"]):
        """Sets the relations of this SpgType.


        :param relations: The relations of this SpgType.  # noqa: E501
        :type: list[Relation]
        """

        if relations is None:
            return

        self._rest_model.relations = [relation.to_rest() for relation in relations]

    def add_relation(self, relation: Type["Relation"]):
        """Adds a relation to this SpgType.


        :param relation: The relation to add.  # noqa: E501
        :type: Relation
        """

        relation.alter_operation = AlterOperationEnum.Create
        self._rest_model.relations.append(relation.to_rest())
        return self

    @property
    def alter_operation(self) -> Optional[AlterOperationEnum]:
        """Gets the alter_operation of this SpgType.  # noqa: E501


        :return: The alter_operation of this SpgType.  # noqa: E501
        :rtype: AlterOperationEnum
        """
        alter_operation = self._rest_model.alter_operation
        return AlterOperationEnum(alter_operation) if alter_operation else None

    @alter_operation.setter
    def alter_operation(self, alter_operation: AlterOperationEnum):
        """Sets the alter_operation of this SpgType.


        :param alter_operation: The alter_operation of this SpgType.  # noqa: E501
        :type: AlterOperationEnum
        """
        self._rest_model.alter_operation = alter_operation

    @staticmethod
    def by_type_enum(type_enum: str):
        """Reflection from type enum to subclass object of BaseSpgType."""

        import knext.schema.model.spg_type as spg_type

        class_obj = getattr(spg_type, f"{SpgTypeEnum(type_enum).name}Type")
        return class_obj

    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in self.__annotations__.items():
            value = getattr(self, attr)
            if isinstance(value, typing.List):
                result[attr] = list(
                    map(lambda x: x.to_dict() if hasattr(x, "to_dict") else x, value)
                )
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, typing.Dict):
                result[attr] = dict(
                    map(
                        lambda item: (
                            (item[0], item[1].to_dict())
                            if hasattr(item[1], "to_dict")
                            else item
                        ),
                        value.items(),
                    )
                )
            else:
                result[attr] = value

        return result

    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())

    def to_rest(self):
        """Returns the REST model of this SpgType"""
        return self._rest_model

    def __repr__(self):
        """For `print` and `pprint`"""
        return self.to_str()

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        if not isinstance(other, self.__class__):
            return False

        return self.to_dict() == other.to_dict()

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        if not isinstance(other, self.__class__):
            return True

        return self.to_dict() != other.to_dict()
