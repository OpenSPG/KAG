# -*- coding: utf-8 -*-
import os
from kag.common.conf import KAG_CONFIG
from kag.builder.model.chunk import Chunk
from kag.interface import ExtractorABC
from kag.builder.model.sub_graph import SubGraph

llm_config = KAG_CONFIG.all_config["llm"]

pwd = os.path.dirname(__file__)


def test_kag_extractor():
    conf = {
        "type": "schema_free",
        "llm": llm_config,
        "ner_prompt": {"type": "default_ner"},
    }

    extractor = ExtractorABC.from_config(conf)
    with open(os.path.join(pwd, "../data/test_txt.txt"), "r") as reader:
        content = reader.read()
    chunk = Chunk(id="111", name="test", content=content)
    subgraph = extractor.invoke(chunk)[0]
    print(subgraph)
    print(type(subgraph))
    assert isinstance(subgraph, SubGraph)


def test_spg_extractor():
    conf = {
        "type": "schema_constraint",
        "llm": llm_config,
        "ner_prompt": {"type": "default_ner"},
    }

    extractor = ExtractorABC.from_config(conf)
    with open(os.path.join(pwd, "../data/test_txt.txt"), "r") as reader:
        content = reader.read()
    chunk = Chunk(id="111", name="test", content=content)
    subgraph = extractor.invoke(chunk)[0]
    print(subgraph)
    print(type(subgraph))
    assert isinstance(subgraph, SubGraph)
