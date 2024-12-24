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

from typing import List, Type, Dict

from knext.schema.model.base import BaseProperty
from knext.schema.model.property import Property


class Relation(BaseProperty):
    """Relation Model."""

    name: str
    object_type_name: str
    name_zh: str
    desc: str
    sub_properties: Dict[str, Type["Property"]]
    logical_rule: str

    def __init__(
        self,
        name: str,
        object_type_name: str,
        name_zh: str = None,
        desc: str = None,
        sub_properties: List[Property] = None,
        logical_rule: str = None,
        **kwargs
    ):
        super().__init__(
            name=name,
            object_type_name=object_type_name,
            name_zh=name_zh,
            desc=desc,
            sub_properties=sub_properties,
            logical_rule=logical_rule,
            **kwargs
        )

    @property
    def is_dynamic(self) -> bool:
        """Gets the is_dynamic of this Property/Relation.  # noqa: E501


        :return: The is_dynamic of this Property/Relation.  # noqa: E501
        :rtype: str
        """
        return self._rest_model.is_dynamic

    @is_dynamic.setter
    def is_dynamic(self, is_dynamic: bool):
        """Sets the is_dynamic of this Property/Relation.


        :param is_dynamic: The is_dynamic of this Property/Relation.  # noqa: E501
        :type: bool
        """

        self._rest_model.is_dynamic = is_dynamic
