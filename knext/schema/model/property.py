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

from typing import List, Type, Union, Dict

from knext.schema.model.base import (
    ConstraintTypeEnum,
    PropertyGroupEnum,
    BaseProperty,
    IndexTypeEnum,
)


class Property(BaseProperty):
    """Property Model."""

    name: str
    object_type_name: str
    name_zh: str
    desc: str
    property_group: PropertyGroupEnum
    sub_properties: Dict[str, Type["Property"]]
    constraint: Dict[ConstraintTypeEnum, Union[str, List[str]]]
    logical_rule: str
    index_type: IndexTypeEnum

    def __init__(
        self,
        name: str,
        object_type_name: str,
        name_zh: str = None,
        desc: str = None,
        property_group: PropertyGroupEnum = None,
        sub_properties: List[Type["Property"]] = None,
        constraint: Dict[ConstraintTypeEnum, Union[str, List[str]]] = None,
        logical_rule: str = None,
        index_type: IndexTypeEnum = None,
        **kwargs
    ):
        super().__init__(
            name=name,
            object_type_name=object_type_name,
            name_zh=name_zh,
            desc=desc,
            property_group=property_group,
            sub_properties=sub_properties,
            constraint=constraint,
            logical_rule=logical_rule,
            index_type=index_type,
            **kwargs
        )
