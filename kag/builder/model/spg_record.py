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
        """
        Initializes a new instance of the SPGRecord class.

        Args:
            spg_type_name (SPGTypeName): The type name of the SPG entity.
        """
        self._spg_type_name = spg_type_name
        self._properties = {}
        self._relations = {}

    @property
    def id(self) -> str:
        """
        Gets the ID of the SPGRecord.

        Returns:
            str: The ID of the SPGRecord.
        """
        return self.get_property("id", "")

    @property
    def name(self) -> str:
        """
        Gets the name of the SPGRecord.

        Returns:
            str: The name of the SPGRecord.
        """
        return self.get_property("name", self.id)

    @property
    def spg_type_name(self) -> SPGTypeName:
        """
        Gets the SPG type name of this SPGRecord.

        Returns:
            SPGTypeName: The SPG type name of this SPGRecord.
        """
        return self._spg_type_name

    @spg_type_name.setter
    def spg_type_name(self, spg_type_name: SPGTypeName):
        """
        Sets the SPG type name of this SPGRecord.

        Args:
            spg_type_name (SPGTypeName): The SPG type name of this SPGRecord.
        """
        self._spg_type_name = spg_type_name

    @property
    def properties(self) -> Dict[PropertyName, str]:
        """
        Gets the properties of this SPGRecord.

        Returns:
            Dict[PropertyName, str]: The properties of this SPGRecord.
        """
        return self._properties

    @properties.setter
    def properties(self, properties: Dict[PropertyName, str]):
        """
        Sets the properties of this SPGRecord.

        Args:
            properties (Dict[PropertyName, str]): The properties of this SPGRecord.
        """
        self._properties = properties

    @property
    def relations(self) -> Dict[str, str]:
        """
        Gets the relations of this SPGRecord.

        Returns:
            Dict[str, str]: The relations of this SPGRecord.
        """
        return self._relations

    @relations.setter
    def relations(self, relations: Dict[str, str]):
        """
        Sets the relations of this SPGRecord.

        Args:
            relations (Dict[str, str]): The relations of this SPGRecord.
        """
        self._relations = relations

    def get_property(
        self, property_name: PropertyName, default_value: str = None
    ) -> str:
        """
        Gets a property of this SPGRecord by name.

        Args:
            property_name (PropertyName): The property name.
            default_value (str, optional): If the property value is None, the default_value will be returned. Defaults to None.

        Returns:
            str: The property value.
        """
        return self.properties.get(property_name, default_value)

    def upsert_property(self, property_name: PropertyName, value: str):
        """
        Upserts a property of this SPGRecord.

        Args:
            property_name (PropertyName): The updated property name.
            value (str): The updated property value.
        """
        self.properties[property_name] = value
        return self

    def append_property(self, property_name: PropertyName, value: str):
        """
        Appends a property of this SPGRecord.

        Args:
            property_name (PropertyName): The updated property name.
            value (str): The updated property value.
        """
        property_value = self.get_property(property_name)
        if property_value:
            property_value_list = property_value.split(",")
            if value not in property_value_list:
                self.properties[property_name] = property_value + "," + value
        else:
            self.properties[property_name] = value
        return self

    def upsert_properties(self, properties: Dict[PropertyName, str]):
        """
        Upserts properties of this SPGRecord.

        Args:
            properties (Dict[PropertyName, str]): The updated properties.
        """
        self.properties.update(properties)
        return self

    def remove_property(self, property_name: PropertyName):
        """
        Removes a property of this SPGRecord.

        Args:
            property_name (PropertyName): The property name.
        """
        self.properties.pop(property_name)
        return self

    def remove_properties(self, property_names: List[PropertyName]):
        """
        Removes properties by given names.

        Args:
            property_names (List[PropertyName]): A list of property names.
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
        """
        Gets a relation of this SPGRecord by name.

        Args:
            relation_name (RelationName): The relation name.
            object_type_name (SPGTypeName): The object SPG type name.
            default_value (str, optional): If the relation value is None, the default_value will be returned. Defaults to None.

        Returns:
            str: The relation value.
        """
        return self.relations.get(relation_name + "#" + object_type_name, default_value)

    def upsert_relation(
        self, relation_name: RelationName, object_type_name: SPGTypeName, value: str
    ):
        """
        Upserts a relation of this SPGRecord.

        Args:
            relation_name (RelationName): The updated relation name.
            object_type_name (SPGTypeName): The object SPG type name.
            value (str): The updated relation value.
        """
        self.relations[relation_name + "#" + object_type_name] = value
        return self

    def upsert_relations(self, relations: Dict[Tuple[RelationName, SPGTypeName], str]):
        """
        Upserts relations of this SPGRecord.

        Args:
            relations (Dict[Tuple[RelationName, SPGTypeName], str]): The updated relations.
        """
        for (relation_name, object_type_name), value in relations.items():
            self.relations[relation_name + "#" + object_type_name] = value
        return self

    def remove_relation(
        self, relation_name: RelationName, object_type_name: SPGTypeName
    ):
        """
        Removes a relation of this SPGRecord.

        Args:
            relation_name (RelationName): The relation name.
            object_type_name (SPGTypeName): The object SPG type name.
        """
        self.relations.pop(relation_name + "#" + object_type_name)
        return self

    def remove_relations(self, relation_names: List[Tuple[RelationName, SPGTypeName]]):
        """
        Removes relations by given names.

        Args:
            relation_names (List[Tuple[RelationName, SPGTypeName]]): A list of relation names.
        """
        for relation_name, object_type_name in relation_names:
            self.relations.pop(relation_name + "#" + object_type_name)
        return self

    def to_str(self):
        """
        Returns the string representation of the model.

        Returns:
            str: The string representation of the model.
        """
        return pprint.pformat(self.__dict__())

    def to_dict(self):
        """
        Returns the model properties as a dict.

        Returns:
            dict: The model properties as a dict.
        """

        return {
            "spgTypeName": self.spg_type_name,
            "properties": {
                **self.properties,
                **self.relations,
            },
        }

    def __dict__(self):
        """
        Returns this SPGRecord as a dict.

        Returns:
            dict: This SPGRecord as a dict.
        """
        return {
            "spgTypeName": self.spg_type_name,
            "properties": self.properties,
            "relations": self.relations,
        }

    @classmethod
    def from_dict(cls, input: Dict[str, Any]):
        """
        Returns the model from a dict.

        Args:
            input (Dict[str, Any]): The input dictionary.

        Returns:
            SPGRecord: The model from the input dictionary.
        """
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
        """
        For `print` and `pprint`.

        Returns:
            str: The string representation of the model.
        """
        return pprint.pformat(self.__dict__())
