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
from typing import Dict, Any, List, Tuple
from knext.schema.model.schema_helper import (
    SPGTypeName,
    PropertyName,
    RelationName,
)


class SPGRecord:
    """Data structure in operator, used to store entity information."""

    def __init__(self, spg_type_name: SPGTypeName):
        self._spg_type_name = spg_type_name
        self._properties = {}
        self._relations = {}

    @property
    def id(self) -> str:
        return self.get_property("id", "")

    @property
    def name(self) -> str:
        return self.get_property("name", self.id)

    @property
    def spg_type_name(self) -> SPGTypeName:
        """Gets the spg_type_name of this SPGRecord.  # noqa: E501


        :return: The spg_type_name of this SPGRecord.  # noqa: E501
        :rtype: str
        """
        return self._spg_type_name

    @spg_type_name.setter
    def spg_type_name(self, spg_type_name: SPGTypeName):
        """Sets the spg_type_name of this SPGRecord.


        :param spg_type_name: The spg_type_name of this SPGRecord.  # noqa: E501
        :type: str
        """
        self._spg_type_name = spg_type_name

    @property
    def properties(self) -> Dict[PropertyName, str]:
        """Gets the properties of this SPGRecord.  # noqa: E501


        :return: The properties of this SPGRecord.  # noqa: E501
        :rtype: dict
        """
        return self._properties

    @properties.setter
    def properties(self, properties: Dict[PropertyName, str]):
        """Sets the properties of this SPGRecord.


        :param properties: The properties of this SPGRecord.  # noqa: E501
        :type: dict
        """
        self._properties = properties

    @property
    def relations(self) -> Dict[str, str]:
        """Gets the relations of this SPGRecord.  # noqa: E501


        :return: The relations of this SPGRecord.  # noqa: E501
        :rtype: dict
        """
        return self._relations

    @relations.setter
    def relations(self, relations: Dict[str, str]):
        """Sets the properties of this SPGRecord.


        :param relations: The relations of this SPGRecord.  # noqa: E501
        :type: dict
        """
        self._relations = relations

    def get_property(
        self, property_name: PropertyName, default_value: str = None
    ) -> str:
        """Gets a property of this SPGRecord by name.  # noqa: E501


        :param property_name: The property name.  # noqa: E501
        :param default_value: If property value is None, the default_value will be return.  # noqa: E501
        :return: A property value.  # noqa: E501
        :rtype: str
        """
        return self.properties.get(property_name, default_value)

    def upsert_property(self, property_name: PropertyName, value: str):
        """Upsert a property of this SPGRecord.  # noqa: E501


        :param property_name: The updated property name.  # noqa: E501
        :param value: The updated property value.  # noqa: E501
        :type: str
        """
        self.properties[property_name] = value
        return self

    def append_property(self, property_name: PropertyName, value: str):
        """Append a property of this SPGRecord.  # noqa: E501


        :param property_name: The updated property name.  # noqa: E501
        :param value: The updated property value.  # noqa: E501
        :type: str
        """
        property_value = self.get_property(property_name)
        if property_value:
            property_value_list = property_value.split(',')
            if value not in property_value_list:
                self.properties[property_name] = property_value + ',' + value
        else:
            self.properties[property_name] = value
        return self

    def upsert_properties(self, properties: Dict[PropertyName, str]):
        """Upsert properties of this SPGRecord.  # noqa: E501


        :param properties: The updated properties.  # noqa: E501
        :type: dict
        """
        self.properties.update(properties)
        return self

    def remove_property(self, property_name: PropertyName):
        """Removes a property of this SPGRecord.  # noqa: E501


        :param property_name: The property name.  # noqa: E501
        :type: str
        """
        self.properties.pop(property_name)
        return self

    def remove_properties(self, property_names: List[PropertyName]):
        """Removes properties by given names.  # noqa: E501


        :param property_names: A list of property names.  # noqa: E501
        :type: list
        """
        for property_name in property_names:
            self.properties.pop(property_name)
        return self

    def get_relation(
        self,
        relation_name: RelationName,
        object_type_name: SPGTypeName,
        default_value: str = None,
    ) -> str:
        """Gets a relation of this SPGRecord by name.  # noqa: E501


        :param relation_name: The relation name.  # noqa: E501
        :param object_type_name: The object SPG type name.  # noqa: E501
        :param default_value: If property value is None, the default_value will be return.  # noqa: E501
        :return: A relation value.  # noqa: E501
        :rtype: str
        """
        return self.relations.get(relation_name + "#" + object_type_name, default_value)

    def upsert_relation(
        self, relation_name: RelationName, object_type_name: SPGTypeName, value: str
    ):
        """Upsert a relation of this SPGRecord.  # noqa: E501


        :param relation_name: The updated relation name.  # noqa: E501
        :param object_type_name: The object SPG type name.  # noqa: E501
        :param value: The updated relation value.  # noqa: E501
        :type: str
        """
        self.relations[relation_name + "#" + object_type_name] = value
        return self

    def upsert_relations(self, relations: Dict[Tuple[RelationName, SPGTypeName], str]):
        """Upsert relations of this SPGRecord.  # noqa: E501


        :param relations: The updated relations.  # noqa: E501
        :type: dict
        """
        for (relation_name, object_type_name), value in relations.items():
            self.relations[relation_name + "#" + object_type_name] = value
        return self

    def remove_relation(
        self, relation_name: RelationName, object_type_name: SPGTypeName
    ):
        """Removes a relation of this SPGRecord.  # noqa: E501


        :param relation_name: The relation name.  # noqa: E501
        :param object_type_name: The object SPG type name.  # noqa: E501
        :type: str
        """
        self.relations.pop(relation_name + "#" + object_type_name)
        return self

    def remove_relations(self, relation_names: List[Tuple[RelationName, SPGTypeName]]):
        """Removes relations by given names.  # noqa: E501


        :param relation_names: A list of relation names.  # noqa: E501
        :type: list
        """
        for (relation_name, object_type_name) in relation_names:
            self.relations.pop(relation_name + "#" + object_type_name)
        return self

    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.__dict__())

    def to_dict(self):
        """Returns the model properties as a dict"""

        return {
            "spgTypeName": self.spg_type_name,
            "properties": {
                **self.properties,
                **self.relations,
            },
        }

    def __dict__(self):
        """Returns this SPGRecord as a dict"""
        return {
            "spgTypeName": self.spg_type_name,
            "properties": self.properties,
            "relations": self.relations,
        }

    @classmethod
    def from_dict(cls, input: Dict[str, Any]):
        """Returns the model from a dict"""
        spg_type_name = input.get("spgTypeName")
        _cls = cls(spg_type_name)
        properties = input.get("properties")
        for k, v in properties.items():
            if "#" in k:
                relation_name, object_type_name = k.split("#")
                _cls.relations.update({relation_name + "#" + object_type_name: v})
            else:
                _cls.properties.update({k: v})

        return _cls

    def __repr__(self):
        """For `print` and `pprint`"""
        return pprint.pformat(self.__dict__())
