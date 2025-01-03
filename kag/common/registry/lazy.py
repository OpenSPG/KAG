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

import inspect
from pyhocon import ConfigTree
from typing import Callable, Generic, TypeVar, Type, Union, Any

T = TypeVar("T")


class Lazy(Generic[T]):
    """
    This class is for use when constructing objects using `Registrable`, when an argument to a
    constructor has a _sequential dependency_ with another argument to the same constructor.

    For example, in a `Trainer` class you might want to take a `Model` and an `Optimizer` as arguments,
    but the `Optimizer` needs to be constructed using the parameters from the `Model`. You can give
    the type annotation `Lazy[Optimizer]` to the optimizer argument, then inside the constructor
    call `optimizer.construct(parameters=model.parameters)`.

    This is only recommended for use when you have registered a `@classmethod` as the constructor
    for your class, instead of using `__init__`.  Having a `Lazy[]` type annotation on an argument
    to an `__init__` method makes your class completely dependent on being constructed using the
    `Registrable` pipeline, which is not a good idea.

    The actual implementation here is incredibly simple; the logic that handles the lazy
    construction is actually found in `Registrable`, where we have a special case for a `Lazy` type
    annotation.

    ```python
    @classmethod
    def my_constructor(
        cls,
        some_object: Lazy[MyObject],
        optional_object: Lazy[MyObject] = None,
        required_object_with_default: Lazy[MyObject] = Lazy(MyObjectDefault),
    ) -> MyClass:
        obj1 = some_object.construct()
        obj2 = None if optional_object is None else optional_object.construct()
        obj3 = required_object_with_default.construct()
    ```

    """

    def __init__(
        self, constructor: Union[Type[T], Callable[..., T]], original_params: Any = None
    ):
        constructor_to_use: Callable[..., T]

        if inspect.isclass(constructor):

            def constructor_to_use(**kwargs):
                return constructor.from_config(ConfigTree({}), **kwargs)

        else:
            constructor_to_use = constructor

        self._constructor = constructor_to_use
        self.original_params = original_params

    def construct(self, **kwargs) -> T:
        return self._constructor(**kwargs)
