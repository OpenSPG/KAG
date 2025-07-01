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
import importlib
import logging
import functools
import collections
import traceback

from pathlib import Path
from pyhocon import ConfigTree, ConfigFactory
from pyhocon.exceptions import ConfigMissingException
from copy import deepcopy
from collections import defaultdict
from typing import (
    TypeVar,
    Type,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    cast,
    Any,
    get_origin,
    get_args,
    Mapping,
    Set,
    Iterable,
)
from kag.common.registry.lazy import Lazy


class ConfigurationError(Exception):
    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def __str__(self):
        return self.message


logger = logging.getLogger()

RegistrableType = TypeVar("RegistrableType", bound="Registrable")


def str_to_bool(s):
    if isinstance(s, bool):
        return s
    s = s.lower()
    if s == "true":
        return True
    elif s == "false":
        return False
    elif s == "none":
        return None
    elif s == "0":
        return False
    elif s == "1":
        return True
    else:
        raise ValueError(f"not supported string {s}")


def auto_setattr(func, self, args, kwargs):
    # handle default values
    def try_setattr(attr, val):
        try:
            setattr(self, attr, val)
        except Exception as e:
            logger.warning(
                f"set attribute {attr} of type {type(self)} error, info: {e}"
            )

    attrs, varargs, varkw, defaults = (inspect.getfullargspec(func))[:4]
    if defaults:
        for attr, val in zip(reversed(attrs), reversed(defaults)):
            try_setattr(attr, val)
    # handle positional arguments
    positional_attrs = attrs[1:]
    for attr, val in zip(positional_attrs, args):
        try_setattr(attr, val)

    if kwargs:
        for attr, val in kwargs.items():
            try_setattr(attr, val)


def autoargs(func):
    """A decorator which automatically assign the inputs of the function to self PRIOR to executing
    the function."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        auto_setattr(func, self, args=args, kwargs=kwargs)

        try:
            ret = func(self, *args, **kwargs)
        except TypeError as e:
            raise TypeError(
                "call %s.%s failed, details:%s"
                % (type(self).__name__, func.__name__, str(e))
            )

        return ret

    return wrapper


def can_accept_arg(obj, arg: str) -> bool:
    """
    Checks whether the provided obj takes a certain arg.
    If it's a class, we're really checking whether its constructor does.
    If it's a function or method, we're checking the object itself.
    Otherwise, we raise an error.
    """
    if inspect.isclass(obj):
        signature = inspect.signature(obj.__init__)
    elif inspect.ismethod(obj) or inspect.isfunction(obj):
        signature = inspect.signature(obj)
    else:
        raise ConfigurationError(f"object {obj} is not callable")
    return arg in signature.parameters


def can_accept_kwargs(obj) -> bool:
    """
    Checks whether a provided object takes in any positional arguments.
    Similar to accept_arg, we do this for both the __init__ function of
    the class or a function / method
    Otherwise, we raise an error
    """
    if inspect.isclass(obj):
        signature = inspect.signature(obj.__init__)
    elif inspect.ismethod(obj) or inspect.isfunction(obj):
        signature = inspect.signature(obj)
    else:
        raise ConfigurationError(f"object {obj} is not callable")
    return any(
        p.kind == inspect.Parameter.VAR_KEYWORD  # type: ignore
        for p in signature.parameters.values()
    )


def can_construct_from_config(type_: Type) -> bool:
    if type_ in [str, int, float, bool]:
        return True
    origin = getattr(type_, "__origin__", None)
    if origin == Lazy:
        return True
    elif origin:
        if hasattr(type_, "from_config"):
            return True
        args = getattr(type_, "__args__")
        return all(can_construct_from_config(arg) for arg in args)

    return hasattr(type_, "from_config")


def remove_optional(annotation: type) -> type:
    """
    Remove Optional[X](alias of Union[T, None]) annotations by filtering out NoneType from Union[X, NoneType].
    """
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin == Union:
        return Union[tuple([arg for arg in args if arg != type(None)])]  # noqa
    else:
        return annotation


def extract_parameters(
    cls: Type[RegistrableType],
    constructor: Union[
        Callable[..., RegistrableType], Callable[[RegistrableType], None]
    ] = None,
) -> Dict[str, Any]:
    """
    Extracts the parameters from the constructor of a class, excluding any variable positional parameters.

    Args:
        cls (Type[RegistrableType]): The class whose constructor parameters are to be extracted.
        constructor (Union[Callable[..., RegistrableType], Callable[[RegistrableType], None]], optional): The constructor method to inspect. Defaults to cls.__init__.

    Returns:
        Dict[str, Any]: A dictionary containing the parameters of the constructor, excluding any variable positional parameters.
    """
    if constructor is None:
        constructor = cls.__init__
    if isinstance(constructor, str):
        constructor = getattr(cls, constructor)
    signature = inspect.signature(constructor)
    parameters = dict(signature.parameters)

    var_positional_key = None
    for param in parameters.values():
        if param.kind == param.VAR_POSITIONAL:
            var_positional_key = param.name
            break
    if var_positional_key:
        del parameters[var_positional_key]
    return parameters


def create_kwargs(
    constructor: Callable[..., RegistrableType],
    cls: Type[RegistrableType],
    actual_params: ConfigTree,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Given some class, a `Params` object, and potentially other keyword arguments,
    create a dict of keyword args suitable for passing to the class's constructor.

    The function does this by finding the class's constructor, matching the constructor
    arguments to entries in the `params` object, and instantiating values for the parameters
    using the type annotation and possibly a from_config method.

    """
    # Get the signature of the constructor.

    kwargs: Dict[str, Any] = {}

    formal_parameters = extract_parameters(cls, constructor)
    accepts_kwargs = False

    # Iterate over all the constructor parameters and their annotations.
    for param_name, param in formal_parameters.items():
        if param_name == "self":
            continue
        if param.kind == param.VAR_KEYWORD:
            # if constructor takes **kwargs, we will put all the remaining params to kwargs
            accepts_kwargs = True
            continue

        # annotation = remove_optional(param.annotation)
        constructed_arg = pop_and_construct_arg(
            cls.__name__,
            param_name,
            param.annotation,
            param.default,
            actual_params,
        )
        if constructed_arg is not param.default:
            kwargs[param_name] = constructed_arg

        # If we just ended up constructing the default value for the parameter, we can just omit it.
        # Leaving it in can cause issues with **kwargs in some corner cases, where you might end up
        # with multiple values for a single parameter (e.g., the default value gives you lazy=False
        # for a dataset reader inside **kwargs, but a particular dataset reader actually hard-codes
        # lazy=True - the superclass sees both lazy=True and lazy=False in its constructor).
    # if constructor accepts kwargs, put remainder params to kwargs
    if accepts_kwargs:
        kwargs.update(actual_params)
    return accepts_kwargs, kwargs


def pop_and_construct_arg(
    class_name: str,
    argument_name: str,
    annotation: Type,
    default: Any,
    actual_params: ConfigTree,
) -> Any:
    annotation = remove_optional(annotation)
    popped_params = (
        actual_params.pop(argument_name, default)
        if default != inspect.Parameter.empty
        else actual_params.pop(argument_name)
    )
    if popped_params is None:
        return None

    return construct_arg(
        class_name,
        argument_name,
        popped_params,
        annotation,
        default,
    )


def construct_arg(
    class_name: str,
    argument_name: str,
    popped_params: Any,
    annotation: Type,
    default: Any,
) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)

    optional = default != inspect.Parameter.empty
    # annotation is subclass of Registrable
    if hasattr(annotation, "from_config"):
        if popped_params is default:
            return default
        elif popped_params is not None:
            # If `popped_params` has already been instantiated, use this object directly.
            if isinstance(popped_params, annotation):
                return popped_params
            return annotation.from_config(ConfigFactory.from_dict(popped_params))
        elif not optional:
            # Not optional and not supplied, that's an error!
            raise ConfigurationError(f"expected key {argument_name} for {class_name}")
        else:
            return default

    # If the parameter type is a Python primitive, just pop it off
    # using the correct casting pop_xyz operation.
    elif annotation == int:
        if type(popped_params) in {int, bool, str}:
            return annotation(popped_params)
        else:
            raise TypeError(f"Expected {argument_name} to be a {annotation.__name__}.")
    elif annotation == bool:
        if type(popped_params) in {int, bool}:
            return annotation(popped_params)
        # string likes 'true', 'false', 'none' can be convert to bool correctly
        # NOTE: bool(str) will always return True for nonempty str.
        elif type(popped_params) == str:
            return str_to_bool(popped_params)

    elif annotation == str:
        # Strings are special because we allow casting from Path to str.
        if type(popped_params) == str or isinstance(popped_params, Path):
            return str(popped_params)  # type: ignore
        else:
            raise TypeError(f"Expected {argument_name} to be a string.")
    elif annotation == float:
        # Floats are special because in Python, you can put an int wherever you can put a float.
        # https://mypy.readthedocs.io/en/stable/duck_type_compatibility.html
        if type(popped_params) in {int, float, str}:
            return popped_params
        else:
            raise TypeError(f"Expected {argument_name} to be numeric.")

    elif annotation == ConfigTree:
        if isinstance(popped_params, ConfigTree):
            return popped_params
        elif type(popped_params) in {collections.abc.Mapping, Mapping, Dict, dict}:
            return ConfigFactory.from_dict(popped_params)
        else:
            raise TypeError(f"Expected {argument_name} to be Dict.")
    # This is special logic for handling types like Dict[str, TokenIndexer],
    # List[TokenIndexer], Tuple[TokenIndexer, Tokenizer], and Set[TokenIndexer],
    # which it creates by instantiating each value from_config and returning the resulting structure.
    elif (
        origin in {collections.abc.Mapping, Mapping, Dict, dict}
        and len(args) == 2
        and can_construct_from_config(args[-1])
    ):
        value_cls = annotation.__args__[-1]

        value_dict = {}

        for key, value_params in popped_params.items():
            value_dict[key] = construct_arg(
                str(value_cls),
                argument_name + "." + key,
                value_params,
                value_cls,
                inspect.Parameter.empty,
            )

        return value_dict

    elif origin in (Tuple, tuple) and all(
        can_construct_from_config(arg) for arg in args
    ):
        value_list = []

        for i, (value_cls, value_params) in enumerate(
            zip(annotation.__args__, popped_params)
        ):
            value = construct_arg(
                str(value_cls),
                argument_name + f".{i}",
                value_params,
                value_cls,
                inspect.Parameter.empty,
            )
            value_list.append(value)

        return tuple(value_list)

    elif origin in (Set, set) and len(args) == 1 and can_construct_from_config(args[0]):
        value_cls = annotation.__args__[0]

        value_set = set()

        for i, value_params in enumerate(popped_params):
            value = construct_arg(
                str(value_cls),
                argument_name + f".{i}",
                value_params,
                value_cls,
                inspect.Parameter.empty,
            )
            value_set.add(value)

        return value_set

    elif origin == Union:
        # Storing this so we can recover it later if we need to.
        backup_params = deepcopy(popped_params)

        # We'll try each of the given types in the union sequentially, returning the first one that
        # succeeds.
        all_err_msg = []
        for arg_annotation in args:
            try:
                return construct_arg(
                    str(arg_annotation),
                    argument_name,
                    popped_params,
                    arg_annotation,
                    default,
                )
            except (
                ValueError,
                TypeError,
                ConfigurationError,
                AttributeError,
                ConfigMissingException,
            ) as e:
                # Our attempt to construct the argument may have modified popped_params, so we
                # restore it here.

                popped_params = deepcopy(backup_params)
                err_msg = f" Exception caught for constructing {arg_annotation}: {e}\n{traceback.format_exc()}"
                all_err_msg.append(err_msg)
        # If none of them succeeded, we crash.
        info_separatpr = f"{'='*40}\n"
        info = (
            f"Failed to construct argument {argument_name} with type {annotation}, details:\n"
            f"{'='*80}"
            f"\n{info_separatpr.join(all_err_msg)}"
        )

        raise ConfigurationError(info)
    elif origin == Lazy:
        if popped_params is default:
            return default

        value_cls = args[0]

        def constructor(**kwargs):
            return value_cls.from_config(params=deepcopy(popped_params), **kwargs)

        return Lazy(constructor, deepcopy(popped_params))  # type: ignore

    # For any other kind of iterable, we will just assume that a list is good enough, and treat
    # it the same as List. This condition needs to be at the end, so we don't catch other kinds
    # of Iterables with this branch.
    elif (
        origin in {collections.abc.Iterable, Iterable, List, list}
        and len(args) == 1
        and can_construct_from_config(args[0])
    ):
        value_cls = annotation.__args__[0]

        value_list = []

        for i, value_params in enumerate(popped_params):
            value = construct_arg(
                str(value_cls),
                argument_name + f".{i}",
                value_params,
                value_cls,
                inspect.Parameter.empty,
            )
            value_list.append(value)

        return value_list

    else:
        return popped_params


class Registrable:
    """
    This class is motivated by the original work:
    https://github.com/allenai/allennlp/blob/main/allennlp/common/from_params.py
    """

    _registry: Dict[Type, Dict[str, Tuple[Type, Optional[str]]]] = defaultdict(dict)
    default_implementation: Optional[str] = None
    NonParams = []

    @autoargs
    def __init__(self, **kwargs):
        pass

    @classmethod
    def register(
        cls: Type[RegistrableType],
        name: str,
        constructor: str = None,
        exist_ok: bool = True,
        as_default=False,
    ):
        registry = Registrable._registry[cls]
        if as_default:
            cls.default_implementation = name

        def add_subclass_to_registry(subclass: Type[RegistrableType]):
            # Add to registry, raise an error if key has already been used.
            if name in registry:
                if exist_ok:
                    message = (
                        f"{name} of class {subclass} has already been registered as {registry[name][0].__name__}, but "
                        f"exist_ok=True, so overwriting with {cls.__name__}"
                    )
                    logger.info(message)
                else:
                    message = (
                        f"Cannot register {name} as {cls.__name__}; "
                        f"name already in use for {registry[name][0].__name__}"
                    )
                    raise ConfigurationError(message)
            if inspect.isclass(subclass):
                # not wrapped.
                if not hasattr(subclass.__init__, "__wrapped__"):
                    subclass.__init__ = autoargs(subclass.__init__)

            registry[name] = (subclass, constructor)

            return subclass

        return add_subclass_to_registry

    @classmethod
    def by_name(
        cls: Type[RegistrableType], name: str
    ) -> Callable[..., RegistrableType]:
        """
        Returns a callable function that constructs an argument of the registered class.  Because
        you can register particular functions as constructors for specific names, this isn't
        necessarily the `__init__` method of some class.
        """
        subclass, constructor = cls.resolve_class_name(name)
        if not constructor:
            return subclass
        else:
            return getattr(subclass, constructor)

    @classmethod
    def resolve_class_name(
        cls: Type[RegistrableType], name: str
    ) -> Tuple[Type[RegistrableType], Optional[str]]:
        if name in Registrable._registry[cls]:
            subclass, constructor = Registrable._registry[cls][name]
            return subclass, constructor
        elif "." in name:
            # This might be a fully qualified class name, so we'll try importing its "module"
            # and finding it there.
            parts = name.split(".")
            submodule = ".".join(parts[:-1])
            class_name = parts[-1]

            try:
                module = importlib.import_module(submodule)
            except ModuleNotFoundError:
                raise ConfigurationError(
                    f"tried to interpret {name} as a path to a class "
                    f"but unable to import module {submodule}"
                )

            try:
                subclass = getattr(module, class_name)
                constructor = None
                return subclass, constructor
            except AttributeError:
                raise ConfigurationError(
                    f"tried to interpret {name} as a path to a class "
                    f"but unable to find class {class_name} in {submodule}"
                )

        else:
            # is not a qualified class name
            raise ConfigurationError(
                f"{name} is not a registered name for {cls.__name__}. "
                "You probably need to use the --include-package flag "
                "to load your custom code. Alternatively, you can specify your choices "
                """using fully-qualified paths, e.g. {"model": "my_module.models.MyModel"} """
                "in which case they will be automatically imported correctly."
            )

    @classmethod
    def list_all_registered(cls, with_leaf_classes: bool = False) -> List[str]:
        registered = set()
        for k, v in Registrable._registry.items():
            registered.add(k)
            if with_leaf_classes:
                if isinstance(v, dict):
                    for _, register_cls in v.items():
                        registered.add(register_cls[0])
        return sorted(list(registered), key=lambda x: (x.__module__, x.__name__))

    @classmethod
    def list_available(cls) -> List[str]:
        """List default first if it exists"""
        keys = list(Registrable._registry[cls].keys())
        default = cls.default_implementation

        if default is None:
            return keys
        elif default not in keys:
            raise ConfigurationError(
                f"Default implementation {default} is not registered"
            )
        else:
            return [default] + [k for k in keys if k != default]

    @classmethod
    def list_available_with_detail(cls) -> Dict:
        """List default first if it exists"""
        register_dict = Registrable._registry[cls]
        availables = {}
        for k, v in register_dict.items():
            params = extract_parameters(v[0], v[1])
            required_params = []
            optional_params = []
            sample_config = {"type": k}
            for arg_name, arg_def in params.items():
                if arg_name.strip() == "self":
                    continue
                annotation = arg_def.annotation
                if annotation == inspect.Parameter.empty:
                    annotation = None
                default = arg_def.default
                required = default == inspect.Parameter.empty
                # if default == inspect.Parameter.empty:
                #     default = None
                if required:
                    arg_info = (
                        f"{arg_name}: {annotation.__name__ if annotation else 'Any'}"
                    )
                    required_params.append(arg_info)
                else:
                    arg_info = f"{arg_name}: {annotation.__name__ if annotation else 'Any'} = {default}"
                    optional_params.append(arg_info)
                if required:
                    sample_config[arg_name] = f"Your {arg_name} config"
                else:
                    sample_config[arg_name] = default

                # if default != None:
                #     sample_config[arg_name] = default

            if v[1] is None or v[1] == "__init__":
                constructor_doc_string = inspect.getdoc(getattr(v[0], "__init__"))
            else:
                constructor_doc_string = inspect.getdoc(getattr(v[0], v[1]))
            availables[k] = {
                "class": f"{v[0].__module__}.{v[0].__name__}",
                "doc": inspect.getdoc(v[0]),
                "constructor": constructor_doc_string,
                "params": {
                    "required_params": required_params,
                    "optional_params": optional_params,
                },
                # "default_config": default_conf,
                "sample_useage": f"{cls.__name__}.from_config({sample_config})",
            }
        return availables

    @classmethod
    def from_config(
        cls: Type[RegistrableType],
        params: Union[str, Dict, ConfigTree],
        constructor_to_call: Callable[..., RegistrableType] = None,
        constructor_to_inspect: Union[
            Callable[..., RegistrableType], Callable[[RegistrableType], None]
        ] = None,
    ) -> RegistrableType:
        """
        Instantiate the object via parameters.
        The `constructor_to_call` and `constructor_to_inspect` arguments deal with a bit of
        redirection that we do.  We allow you to register particular `@classmethods` on a class as
        the constructor to use for a registered name.  This lets you, e.g., have a single
        `Vocabulary` class that can be constructed in two different ways, with different names
        registered to each constructor.  In order to handle this, we need to know not just the class
        we're trying to construct (`cls`), but also what method we should inspect to find its
        arguments (`constructor_to_inspect`), and what method to call when we're done constructing
        arguments (`constructor_to_call`).  These two methods are the same when you've used a
        `@classmethod` as your constructor, but they are `different` when you use the default
        constructor (because you inspect `__init__`, but call `cls()`).
        """

        logger.debug(
            f"instantiating class {cls} from params {getattr(params, 'params', params)} "
        )

        if params is None:
            return None

        if isinstance(params, str):
            params = ConfigFactory.from_dict({"type": params})
        elif isinstance(params, collections.abc.Mapping) and not isinstance(
            params, ConfigTree
        ):
            params = ConfigFactory.from_dict(params)
        original_params = deepcopy(params)
        if not isinstance(params, ConfigTree):
            raise ConfigurationError(
                f"from_config was passed a `{params}` object that was not able to convert to `ConfigTree`. "
                "This probably indicates malformed parameters."
                f"This happened when constructing an object of type {cls}."
            )

        registered_subclasses = Registrable._registry.get(cls)
        try:
            # instantiate object from base class
            if registered_subclasses and not constructor_to_call:
                as_registrable = cast(Type[Registrable], cls)
                default_choice = as_registrable.default_implementation
                # call with BaseClass.from_prams, should use `type` to point out which subclasss to use
                choice = params.pop("type", default_choice)
                choices = as_registrable.list_available()
                # if cls has subclass and choice not found in params, we'll instantiate cls itself
                if choice is None:
                    subclass, constructor_name = cls, None
                # invalid choice encountered, raise
                elif choice not in choices:
                    message = (
                        f"{choice} not in acceptable choices for type: {choices}. "
                        "You should make sure the class is correctly registerd. "
                    )
                    raise ConfigurationError(message)

                else:
                    subclass, constructor_name = as_registrable.resolve_class_name(
                        choice
                    )

                # See the docstring for an explanation of what's going on here.
                if not constructor_name:
                    constructor_to_inspect = subclass.__init__
                    constructor_to_call = subclass  # type: ignore
                else:
                    constructor_to_inspect = cast(
                        Callable[..., RegistrableType],
                        getattr(subclass, constructor_name),
                    )
                    constructor_to_call = constructor_to_inspect

                retyped_subclass = cast(Type[RegistrableType], subclass)

                instant = retyped_subclass.from_config(
                    params=params,
                    constructor_to_call=constructor_to_call,
                    constructor_to_inspect=constructor_to_inspect,
                )

                setattr(instant, "__register_type__", choice)
                setattr(instant, "__original_parameters__", original_params)
                # return ins
            else:
                # pop unused type declaration
                register_type = params.pop("type", None)

                if not constructor_to_inspect:
                    constructor_to_inspect = cls.__init__
                if not constructor_to_call:
                    constructor_to_call = cls

                if constructor_to_inspect == object.__init__:
                    # This class does not have an explicit constructor, so don't give it any kwargs.
                    # Without this logic, create_kwargs will look at object.__init__ and see that
                    # it takes *args and **kwargs and look for those.
                    accepts_kwargs, kwargs = False, {}
                else:
                    # This class has a constructor, so create kwargs for it.
                    constructor_to_inspect = cast(
                        Callable[..., RegistrableType], constructor_to_inspect
                    )
                    accepts_kwargs, kwargs = create_kwargs(
                        constructor_to_inspect,
                        cls,
                        params,
                    )

                instant = constructor_to_call(**kwargs)  # type: ignore
                setattr(instant, "__register_type__", register_type)
                setattr(
                    instant,
                    "__constructor_called__",
                    functools.partial(constructor_to_call, **kwargs),
                )
                setattr(instant, "__original_parameters__", original_params)
                # if constructor takes kwargs, they can't be infered from constructor. Therefore we should record
                # which attrs are created by kwargs to correctly restore the configs by `to_config`.
                if accepts_kwargs:
                    remaining_kwargs = set(params)
                    params.clear()
                    setattr(instant, "__from_config_kwargs__", remaining_kwargs)
        except Exception as e:
            logger.info(f"Failed to initialize class {cls}, info: {e}")
            raise e
        if len(params) > 0:
            logger.warn(f"These params are not used for constructing {cls}:\n{params}")
            if "type" in params.keys():
                raise ConfigurationError(
                    f"type is not used for constructing {cls}, but it is passed in params."
                )
        return instant

    def _to_config(self, v):
        """iteratively convert v to params"""
        v_type = type(v)
        if hasattr(v, "to_config"):
            params = v.to_config()
        elif v_type in {collections.abc.Mapping, Mapping, Dict, dict}:
            params = {}
            for subk, subv in v.items():
                params[subk] = self._to_config(subv)
        elif v_type in {
            collections.abc.Iterable,
            Iterable,
            List,
            list,
            Tuple,
            tuple,
            Set,
            set,
        }:
            params = [self._to_config(x) for x in v]
        else:
            params = v
        return params

    def to_config(self) -> ConfigTree:
        """
        convert object back to params.
        Note: If the object is not instantiated by from_config, we can't transfer it back.

        """
        # user can modify object after instantiated, so directly return original params
        # may not be a good way.
        # if hasattr(self, "__original_parameters__") and self.__original_parameters__:
        #     return __original_parameters__
        config = {}

        if hasattr(self, "__register_type__") and self.__register_type__:
            config["type"] = self.__register_type__

        for k, v in self.__constructor_called__.keywords.items():
            if k in self.NonParams:
                continue
            # we don't directly use the value stored in __constructor_called__.keywords, because
            # the value could be a Lazy object, which can't convert to params. Instead, we use
            # attrs of instance itself.
            if hasattr(self, k):
                v = getattr(self, k)
            if hasattr(v, "to_config"):
                conf = v.to_config()
            else:
                conf = self._to_config(v)
            config[k] = conf
        return ConfigFactory.from_dict(config)

    def to_config_with_constructor(self, constructor: str = None) -> ConfigTree:
        """convert object back to params.
        Different from `to_config`, this function can convert objects that are not instantiated by `from_config`,
        but sometimes it may not give correct result.
        For example, suppose the class has more than one constructor, and we instantiated by constructorA but convert
        it to params of constructorB. So use it with caution.
        One should always use `from_config` to instantiate the object and `to_config` to convert it back to params.
        """
        config = {}

        if hasattr(self, "__register_type__") and self.__register_type__:
            config["type"] = self.__register_type__
        if constructor:
            constructor = getattr(self, constructor)
        else:
            constructor = self.__init__

        constructor_params = extract_parameters(type(self), constructor)
        accepts_kwargs = False
        for k, v in constructor_params.items():
            if k in self.NonParams:
                continue

            if v.kind == v.VAR_KEYWORD:
                accepts_kwargs = True
                continue
            # get param instance from class attr
            v_instance = getattr(self, v.name, None)

            if hasattr(v_instance, "to_config"):
                conf = v_instance.to_config()
            else:
                conf = self._to_config(v_instance)
            config[k] = conf
        if accepts_kwargs:
            for k in self.__from_config_kwargs__:
                if hasattr(self, k):
                    config[k] = getattr(self, k)
        return ConfigFactory.from_dict(config)
