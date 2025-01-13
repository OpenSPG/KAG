# -*- coding: utf-8 -*-
import json
from typing import List, Dict, Union
from pyhocon import ConfigTree, ConfigFactory
from kag.common.registry import Registrable, Lazy, Functor
import numpy as np


def test_list_available():
    from kag.interface import LLMClient

    ava = LLMClient.list_available_with_detail()
    print(json.dumps(ava, indent=4))


class MockModel(Registrable):
    def __init__(self, name: str = "mock_model"):
        self.name = name


@MockModel.register("Simple")
class Simple(MockModel):
    def __init__(self, name, age=None):
        pass


@MockModel.register("gaussian")
class Gaussian(MockModel):
    def __init__(
        self, mean: float, variance: float, noise: List[int], attr: ConfigTree
    ):
        pass


@MockModel.register("gaussian_var")
class GaussianVar(MockModel):
    def __init__(
        self,
        mean: float,
        variance: float,
        noise: List[int],
        **kwargs,
    ):
        pass


@MockModel.register("obj_gaussian")
class ObjGaussian(MockModel):
    def __init__(self, mean: float, variance: float, data: List[np.ndarray]):
        pass


@MockModel.register("complex_gaussian_var")
class ComplexGaussianVar(MockModel):
    def __init__(self, list_gaussian: List[GaussianVar], **kwargs):
        pass


@MockModel.register("complex_gaussian")
class ComplexGaussian(MockModel):
    def __init__(
        self, dict_gaussian: Dict[str, Gaussian], list_gaussian: List[Gaussian]
    ):
        pass


@MockModel.register("lazy_gaussian")
class LazyGaussian(MockModel):
    def __init__(
        self,
        gaussian: Lazy[Gaussian],
    ):
        pass


class BaseCount(Registrable):
    pass


@BaseCount.register("default", as_default=True)
@BaseCount.register("from_list_of_ints", constructor="from_list_of_ints")
@BaseCount.register("from_list_of_strings", constructor="from_list_of_strings")
@BaseCount.register("from_string_length", constructor="from_string_length")
class Count(BaseCount):
    def __init__(self, count: int):
        self.count = count

    @classmethod
    def from_list_of_ints(cls, int_list: List[int]):
        ins = cls(len(int_list))
        # we should add attr int_list to instance, otherwise we can't correctly
        # convert it to params.
        setattr(ins, "int_list", int_list)
        return ins

    @classmethod
    def from_list_of_strings(cls, str_list: List[str]):
        ins = cls(len(str_list))
        setattr(ins, "str_list", str_list)
        return ins

    @classmethod
    def from_string_length(cls, string: str):
        ins = cls(len(string))
        setattr(ins, "string", string)
        return ins


class Type1(Registrable):
    pass


class Type2(Registrable):
    pass


class MixBase(Registrable):
    pass


@Type1.register("sub1")
class Sub1(Type1):
    def __init__(self, name1: str):
        pass


@Type1.register("sub11")
class Sub11(Type1):
    def __init__(self, name11: str):
        pass


@Type2.register("sub2")
class Sub2(Type2):
    def __init__(self, name2: str):
        pass


@MixBase.register("mix1")
class Mix1(MixBase):
    def __init__(self, sub: Union[Type1, Type2]):
        pass


@MixBase.register("mix2")
class Mix2(MixBase):
    def __init__(self, sub: Union[Sub1, Sub11, Sub2]):
        pass


class Root(Registrable):
    pass


@Root.register("depth1_1")
class Depth1_1(Root):
    def __init__(self, depth1_1: str):
        pass


@Root.register("depth1_2")
class Depth1_2(Root):
    def __init__(self, depth1_2: str):
        pass


@Root.register("depth2_1")
@Depth1_1.register("depth2_1")
class Depth2_1(Depth1_1):
    def __init__(self, depth2_1: str):
        pass


@Functor.register("simple")
def simple_func(name: "str", age: list = []):
    print(f"name = {name}")
    print(f"age = {age}")
    return sum(age)


@Functor.register("complex")
def complex_func(gaussian: ComplexGaussian):
    return len(gaussian.dict_gaussian), len(gaussian.list_gaussian)


@Functor.register("with_kwargs")
def simple_func3(**kwargs):
    print(f"kwargs = {kwargs}")
    return kwargs


def gen_conf():
    gaussian_0 = {
        "mean": 0,
        "variance": 1,
        "noise": [2, 3, 4],
        "attr": {"name": "xxx", "age": 999},
    }
    gaussian_1 = {
        "mean": 13,
        "variance": 2,
        "noise": [3, 4, 5],
        "attr": {"name": "yyy", "age": 11},
    }
    gaussian_2 = {
        "mean": 20,
        "variance": 3,
        "noise": [4, 5, 6],
        "attr": {"name": "zzz", "age": 234},
    }
    gaussian_3 = {
        "mean": 39,
        "variance": 3,
        "noise": [4, 5, 6],
        "attr": {"name": "xxx", "age": 66},
    }
    gaussian_4 = {
        "mean": 47,
        "variance": 3,
        "noise": [4, 5, 6],
        "attr": {"name": "xxx", "age": 712},
    }
    params_dict = {
        "dict_gaussian": {"0": gaussian_0, "1": gaussian_1},
        "list_gaussian": [gaussian_2, gaussian_3, gaussian_4],
    }

    params = ConfigFactory.from_dict(params_dict)
    return params


def test_from_param():
    params = gen_conf()
    model = ComplexGaussian.from_config(params)
    assert model.list_gaussian[-1].mean == 47


def test_from_param_base():
    params = gen_conf()
    params.put("type", "complex_gaussian")
    model = MockModel.from_config(params)
    assert (
        type(model) is ComplexGaussian
    ), f"expect type ComplexGaussian, got {type(model)}"
    assert model.list_gaussian[-1].mean == 47


def test_to_config():
    params = gen_conf()
    model = ComplexGaussian.from_config(params)
    reconstructed_params = model.to_config()
    reconstructed_model = ComplexGaussian.from_config(reconstructed_params)
    assert len(reconstructed_model.list_gaussian) == 3
    assert reconstructed_model.list_gaussian[-1].mean == 47


def test_multi_constructor():
    # without type key, will use default_implementation
    params = ConfigFactory.from_dict({"count": 32})
    ins = BaseCount.from_config(params)
    reconstructed_params = ins.to_config()
    assert reconstructed_params.count == 32

    params = ConfigFactory.from_dict(
        {"type": "from_list_of_ints", "int_list": [1, 2, 3]}
    )
    ins = BaseCount.from_config(params)
    reconstructed_params = ins.to_config()
    assert reconstructed_params.type == "from_list_of_ints"
    assert reconstructed_params.int_list == [1, 2, 3]

    params = ConfigFactory.from_dict(
        {"type": "from_list_of_strings", "str_list": ["1", "2", "#", "*"]}
    )
    ins = BaseCount.from_config(params)
    reconstructed_params = ins.to_config_with_constructor("from_list_of_strings")
    assert reconstructed_params.type == "from_list_of_strings"
    assert reconstructed_params.str_list == ["1", "2", "#", "*"]


def test_union_type():
    params = ConfigFactory.from_dict(
        {"type": "mix1", "sub": {"type": "sub11", "name11": "sub11"}}
    )
    ins = MixBase.from_config(params)
    assert type(ins.sub) == Sub11
    assert ins.sub.name11 == "sub11"

    params = ConfigFactory.from_dict(
        {"type": "mix1", "sub": {"type": "sub2", "name2": "sub2"}}
    )
    ins = MixBase.from_config(params)
    assert type(ins.sub) == Sub2
    assert ins.sub.name2 == "sub2"

    # for Mix2, type of sub is not required, which has been indicated in __init__
    params = ConfigFactory.from_dict({"type": "mix2", "sub": {"name2": "sub2"}})
    ins = MixBase.from_config(params)
    assert type(ins.sub) == Sub2
    assert ins.sub.name2 == "sub2"


def test_nested():
    conf = ConfigFactory.from_dict({"type": "depth1_1", "depth1_1": "zz"})
    ins = Root.from_config(conf)
    assert type(ins) == Depth1_1
    # instantiate from intermediate class (has both parent class and subclass)
    conf = ConfigFactory.from_dict({"depth1_1": "zz"})
    ins = Depth1_1.from_config(conf)
    assert type(ins) == Depth1_1
    # instantiate from leaf class (have no subclass)
    conf = ConfigFactory.from_dict({"type": "depth1_2", "depth1_2": "zz"})
    ins = Depth1_2.from_config(conf)
    assert type(ins) == Depth1_2
    # instantiate from root class[require extra register declarition]
    conf = ConfigFactory.from_dict({"type": "depth2_1", "depth2_1": "zz"})
    ins = Root.from_config(conf)
    assert type(ins) == Depth2_1
    # instantiate from parent class
    conf = ConfigFactory.from_dict({"type": "depth2_1", "depth2_1": "zz"})
    ins = Depth1_1.from_config(conf)
    assert type(ins) == Depth2_1


def test_pass_dict():
    conf = {"type": "depth1_1", "depth1_1": "zz"}
    ins = Root.from_config(conf)
    assert type(ins) == Depth1_1


def test_with_kwargs():
    conf = {
        "type": "gaussian_var",
        "mean": 1.1,
        "variance": "2.2",
        "noise": [1, 2, 3],
        "less": "more",
        "x": "y",
    }
    res = GaussianVar.from_config(conf)
    assert res.less == "more" and res.x == "y"

    conf = {
        "type": "complex_gaussian_var",
        "less": "more",
        "x": "y",
        "list_gaussian": [
            {"mean": 0.7, "variance": 1.1, "noise": [1, 2, 3], "less": "more", "x": "y"}
        ],
    }
    ComplexGaussianVar.list_available()
    res = ComplexGaussianVar.from_config(conf)
    assert (
        res.less == "more"
        and res.x == "y"
        and res.list_gaussian[0].less == "more"
        and res.list_gaussian[0].x == "y"
    )


def test_with_obj():
    conf = {
        "type": "gaussian_var",
        "mean": 1.1,
        "variance": "2.2",
        "noise": [1, 2, 3],
        "less": "more",
        "x": "y",
    }
    res = GaussianVar.from_config(conf)
    assert res.less == "more" and res.x == "y"

    conf = {
        "type": "complex_gaussian_var",
        "less": "more",
        "x": "y",
        "list_gaussian": [
            {"mean": 0.7, "variance": 1.1, "noise": [1, 2, 3], "less": "more", "x": "y"}
        ],
    }

    res = ComplexGaussianVar.from_config(conf)

    # use object instead of config
    conf["list_gaussian"] = res.list_gaussian
    res2 = ComplexGaussianVar.from_config(conf)

    assert id(res.list_gaussian[0]) == id(
        res2.list_gaussian[0]
    ), "The two objects are different!!"

    data = np.random.rand(128)
    conf = {"mean": 1.1, "variance": 2.2, "data": data}
    res = ObjGaussian.from_config(conf)

    assert data is res.data, "The two objects are different!!"


def test_functor():
    simple_conf = ConfigFactory.from_dict(
        {"type": "simple", "name": "pyfunc", "age": [1, 2, 3]}
    )
    func = Functor.from_config(simple_conf)
    reconstructed_conf = func.to_config()
    reconstructed_func = Functor.from_config(reconstructed_conf)
    assert reconstructed_func() == 6

    complex_conf = ConfigFactory.from_dict({"type": "complex", "gaussian": gen_conf()})
    func = Functor.from_config(complex_conf)
    reconstructed_conf = func.to_config()
    reconstructed_func = Functor.from_config(reconstructed_conf)
    assert reconstructed_func() == (2, 3)

    with_kwargs_conf = ConfigFactory.from_dict(
        {"type": "with_kwargs", "name": "pyfunc"}
    )

    func = Functor.from_config(with_kwargs_conf)
    kwargs = func()
    assert kwargs["name"] == "pyfunc"
