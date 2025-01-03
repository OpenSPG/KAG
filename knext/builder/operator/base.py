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
from typing import Dict, Type


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
