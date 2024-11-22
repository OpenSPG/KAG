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

import logging
import collections
from kag.common.registry.registrable import (
    Registrable,
    ConfigurationError,
    RegistrableType,
    create_kwargs,
)
from types import FunctionType

from typing import Type, Union, Callable, Dict, cast
from functools import partial
from pyhocon import ConfigTree, ConfigFactory

logger = logging.getLogger()


@Registrable.register("functor")
class Functor(Registrable):
    """
    A special `Registrable` for functions(NOT classes).
    It is used to register user defined functions. The registered function will acquire the
    ability of instantiate from configuration.

    e.g.:

    @Functor.register("simple1")
    def simple_func1(name: "str", age: list = []):
        print(f"name = {name}")
        print(f"age = {age}")
        return "+".join(age)
    conf1 = {"type": "simple1", "name": "zzs", "age": ["1", "2", "3"]}
    func = Functor.from_config(conf1)
    func() # same as: simple_func1(name = "zzs", age = ["1", "2", "3"])

    We can also serialize it backto configuration:

    reconstructed_conf = func.to_config()
    reconstructed_func = Functor.from_config(reconstructed_conf)
    """

    def __init__(self, function: partial, register_type: str):
        self._func = function
        self.__register_type__ = register_type

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    @classmethod
    def register(
        cls: Type[RegistrableType],
        name: str,
        exist_ok: bool = True,
        as_default=False,
    ):
        registry = Registrable._registry[cls]
        if as_default:
            cls.default_implementation = name

        def add_function_to_registry(func: FunctionType):
            # Add to registry, raise an error if key has already been used.
            if name in registry:
                if exist_ok:
                    message = (
                        f"{name} has already been registered as {registry[name]}, but "
                        f"exist_ok=True, so overwriting it with {func}"
                    )
                    logger.info(message)
                else:
                    message = (
                        f"Cannot register {name} as {cls.__name__}; "
                        f"name already in use for {registry[name]}"
                    )
                    raise ConfigurationError(message)
            registry[name] = func

            return func

        return add_function_to_registry

    @classmethod
    def from_config(
        cls: Type[RegistrableType],
        params: Union[str, Dict, ConfigTree],
        constructor_to_call: Callable[..., RegistrableType] = None,
        constructor_to_inspect: Union[
            Callable[..., RegistrableType], Callable[[RegistrableType], None]
        ] = None,
    ) -> RegistrableType:

        if isinstance(params, str):
            params = ConfigFactory.from_dict({"type": params})
        elif isinstance(params, collections.abc.Mapping) and not isinstance(
            params, ConfigTree
        ):
            params = ConfigFactory.from_dict(params)

        if not isinstance(params, ConfigTree):
            raise ConfigurationError(
                f"from_config was passed a `{params}` object that was not able to convert to `ConfigTree`. "
                "This probably indicates malformed parameters."
                f"This happened when constructing an object of type {cls}."
            )

        # registered_funcs = Registrable._registry.get(cls)
        registered_funcs = cls.list_available()
        if len(registered_funcs) == 0:
            raise ConfigurationError("There are no registered functions.")

        as_registrable = cast(Type[Functor], cls)
        default_choice = as_registrable.default_implementation
        # call with BaseClass.from_prams, should use `type` to point out which subclasss to use
        choice = params.pop("type", default_choice)
        choices = as_registrable.list_available()

        if choice not in choices:
            message = (
                f"{choice} not in acceptable choices for type: {choices}. "
                "You should make sure the class is correctly registerd. "
            )
            raise ConfigurationError(message)

        function = Registrable._registry[as_registrable][choice]
        # setattr(function, "__register_type__", choice)
        constructor_to_inspect = cast(Callable[..., RegistrableType], function)
        accepts_kwargs, kwargs = create_kwargs(
            constructor_to_inspect,
            cls,
            params,
        )
        if accepts_kwargs:
            params.clear()
        if len(params) > 0:
            raise ConfigurationError(
                f"These params are not used for constructing {cls}:\n{params}"
            )

        return cls(partial(function, **kwargs), choice)

    def to_config(self) -> ConfigTree:
        config = {}

        if hasattr(self, "__register_type__") and self.__register_type__:
            config["type"] = self.__register_type__

        for k, v in self._func.keywords.items():
            if k in self.NonParams:
                continue
            if hasattr(v, "to_config"):
                conf = v.to_config()
            else:
                conf = self._to_config(v)
            config[k] = conf
        return ConfigFactory.from_dict(config)
