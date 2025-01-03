# -*- coding: utf-8 -*-
import copy
import pytest
from kag.interface import VectorizeModelABC


@pytest.mark.skip(reason="Missing API key")
def test_openai_vectorize_model():

    conf = {
        "type": "openai",
        "model": "bge-m3",
        "api_key": "EMPTY",
        "base_url": "http://127.0.0.1:11434/v1",
        "vector_dimensions": 1024,
    }
    vectorize_model = VectorizeModelABC.from_config(copy.deepcopy(conf))
    res = vectorize_model.vectorize("你好")
    assert res is not None


@pytest.mark.skip(reason="Missing model file")
def test_bge_vectorize_model():
    conf = {
        "type": "bge",
        "path": "~/.cache/vectorize_model/BAAI/bge-base-zh-v1.5",
        "url": "xxx",
        "vector_dimensions": 768,
    }

    vectorize_model = VectorizeModelABC.from_config(copy.deepcopy(conf))
    emb = vectorize_model.vectorize("你好")
    assert len(emb) == vectorize_model.get_vector_dimensions()

    vectorize_model2 = VectorizeModelABC.from_config(copy.deepcopy(conf))

    assert id(vectorize_model.model) == id(vectorize_model2.model)


@pytest.mark.skip(reason="Missing model file")
def test_bge_m3_vectorize_model():
    conf = {
        "type": "bge_m3",
        "path": "~/.cache/vectorize_model/BAAI/bge-m3",
        "url": "xxx",
        "vector_dimensions": 1024,
    }

    vectorize_model = VectorizeModelABC.from_config(copy.deepcopy(conf))
    emb = vectorize_model.vectorize("你好")
    assert len(emb) == vectorize_model.get_vector_dimensions()

    vectorize_model2 = VectorizeModelABC.from_config(copy.deepcopy(conf))

    assert id(vectorize_model.model) == id(vectorize_model2.model)


def test_mock_vectorize_model():
    conf = {
        "type": "mock",
        "vector_dimensions": 768,
    }
    vectorize_model = VectorizeModelABC.from_config(copy.deepcopy(conf))
    emb = vectorize_model.vectorize("你好")
    assert len(emb) == vectorize_model.get_vector_dimensions()
    embs = vectorize_model.vectorize(["你好", "再见"])
    assert len(embs) == 2
    for emb in embs:
        assert len(emb) == vectorize_model.get_vector_dimensions()
