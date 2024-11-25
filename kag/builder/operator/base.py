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

from abc import ABC
from typing import Dict, Type, List

from kag.common.cache import LinkCache
from kag.builder.model.spg_record import SPGRecord
from kag.schema.model.schema_helper import SPGTypeName, TripletName

cache = LinkCache()


class BaseOp(ABC):
    """Base class for all user-defined operator functions.

    The execution logic of the operator needs to be implemented in the `eval` method.
    """

    """Operator name."""
    name: str
    """Operator description."""
    desc: str = ""
    """Operator params."""
    params: Dict[str, str] = None

    _registry = {}
    _local_path: str
    _module_path: str
    _version: int
    _has_registered: bool = False

    def __init__(self, params: Dict[str, str] = None):
        self.params = params

    def invoke(self, **kwargs):
        """Used to implement operator execution logic."""
        raise NotImplementedError(
            f"{self.__class__.__name__} need to implement `invoke` method."
        )

    @classmethod
    def register(cls, name: str, local_path: str, module_path: str):
        """
        Register a class as subclass of BaseOp with name and local_path.
        After registration, the subclass object can be inspected by `BaseOp.by_name(op_name)`.
        """

        def add_subclass_to_registry(subclass: Type["BaseOp"]):
            subclass.name = name
            subclass._local_path = local_path
            subclass._module_path = module_path
            if name in cls._registry:
                raise ValueError(
                    f"Operator [{name}] conflict in {subclass._local_path} and {cls.by_name(name)._local_path}."
                )
            cls._registry[name] = subclass
            if hasattr(subclass, "bind_to"):
                subclass.__bases__[0].bind_schemas[subclass.bind_to] = name
            return subclass

        return add_subclass_to_registry

    @classmethod
    def by_name(cls, name: str):
        """Reflection from op name to subclass object of BaseOp."""
        if name in cls._registry:
            subclass = cls._registry[name]
            return subclass
        else:
            raise ValueError(f"{name} is not a registered name for {cls.__name__}. ")

    @property
    def has_registered(self):
        return self._has_registered


class LinkOp(BaseOp, ABC):
    """Base class for all entity link operators."""

    bind_to: SPGTypeName

    bind_schemas: Dict[SPGTypeName, str] = {}

    def __init__(self):
        super().__init__()

    def invoke(self, prop_value: str, properties: Dict[str, str]) -> List[str]:
        raise NotImplementedError(
            f"{self.__class__.__name__} need to implement `invoke` method."
        )


class FuseOp(BaseOp, ABC):
    """
    Base class for all entity fuse operators.
    """

    """"""
    bind_to: SPGTypeName

    bind_schemas: Dict[SPGTypeName, str] = {}

    def __init__(self):
        super().__init__()

    def link(self, subject_record: SPGRecord) -> SPGRecord:
        raise NotImplementedError(
            f"{self.__class__.__name__} need to implement `link` method."
        )

    def merge(self, subject_record: SPGRecord, linked_record: SPGRecord) -> SPGRecord:
        raise NotImplementedError(
            f"{self.__class__.__name__} need to implement `merge` method."
        )

    def invoke(self, subject_records: List[SPGRecord]) -> List[SPGRecord]:
        records = []
        for record in subject_records:
            cache_key = str(self.bind_to) + record.get_property("id", "")
            linked_record = self.link(record)
            if not linked_record:
                records.append(record)
                continue
            merged_record = self.merge(record, linked_record)
            if merged_record:
                cache.put(cache_key, merged_record.get_property("id", ""))
                records.append(merged_record)
        return records


class PredictOp(BaseOp, ABC):
    """Base class for all predict operators."""

    bind_to: TripletName

    bind_schemas: Dict[TripletName, str] = {}

    def __init__(self):
        super().__init__()

    def invoke(self, subject_record: SPGRecord) -> List[SPGRecord]:
        raise NotImplementedError(
            f"{self.__class__.__name__} need to implement `invoke` method."
        )
