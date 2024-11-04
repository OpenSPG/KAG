# -*- coding: utf-8 -*-
import copy
from kag.common.vectorizer import Vectorizer


def test_openai_vectorizer():

    conf = {
        "type": "openai",
        "model": "bge-m3",
        "api_key": "EMPTY",
        "base_url": "http://127.0.0.1:11434/v1",
        "vector_dimensions": 1024,
    }
    vectorizer = Vectorizer.from_config(copy.deepcopy(conf))
    res = vectorizer.vectorize("你好")
    assert res is not None


def test_bge_vectorizer():
    conf = {
        "type": "bge",
        "path": "~/.cache/vectorizer/BAAI/bge-base-zh-v1.5",
        "url": "",
        "vector_dimensions": 768,
    }

    vectorizer = Vectorizer.from_config(copy.deepcopy(conf))
    emb = vectorizer.vectorize("你好")
    assert len(emb) == vectorizer.get_vector_dimensions()

    vectorizer2 = Vectorizer.from_config(copy.deepcopy(conf))

    assert id(vectorizer.model) == id(vectorizer2.model)


def test_bge_m3_vectorizer():
    conf = {
        "type": "bge_m3",
        "path": "~/.cache/vectorizer/BAAI/bge-m3",
        "url": "",
        "vector_dimensions": 1024,
    }

    vectorizer = Vectorizer.from_config(copy.deepcopy(conf))
    emb = vectorizer.vectorize("你好")
    assert len(emb) == vectorizer.get_vector_dimensions()

    vectorizer2 = Vectorizer.from_config(copy.deepcopy(conf))

    assert id(vectorizer.model) == id(vectorizer2.model)
