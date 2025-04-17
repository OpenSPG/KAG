# -*- coding: utf-8 -*-
import os
import copy
import asyncio
from kag.common.conf import KAG_CONFIG
from kag.interface import SplitterABC
from kag.builder.model.chunk import Chunk

llm_config = KAG_CONFIG.all_config["llm"]

pwd = os.path.dirname(__file__)


def test_length_splitter():
    splitter = SplitterABC.from_config(
        {"type": "length", "split_length": 20, "window_length": 10}
    )
    content = "The quick brown fox jumps over the lazy dog. " * 4
    sentences = splitter.split_sentence(content)
    assert len(sentences) == 4

    chunk = Chunk(id=1, name="test", content=content)
    chunks = splitter.invoke(chunk)
    assert len(chunks) > 1


async def atest_length_splitter():
    splitter = SplitterABC.from_config(
        {"type": "length", "split_length": 20, "window_length": 10}
    )
    content = "The quick brown fox jumps over the lazy dog. " * 4
    sentences = splitter.split_sentence(content)
    assert len(sentences) == 4

    chunk = Chunk(id=1, name="test", content=content)
    chunks = await splitter.ainvoke(chunk)
    assert len(chunks) > 1


def test_async_length_splitter():
    asyncio.run(atest_length_splitter())


def test_outline_splitter():
    splitter = SplitterABC.from_config(
        {
            "type": "outline",
            "llm": copy.deepcopy(llm_config),
        }
    )
    with open(os.path.join(pwd, "../data/test_txt.txt"), "r") as reader:
        content = reader.read()
    chunk = Chunk(id=1, name="test", content=content)

    chunks = splitter.invoke(chunk)
    assert len(chunks) > 0 and isinstance(chunks[0], Chunk)


def test_semantic_splitter():
    splitter = SplitterABC.from_config(
        {
            "type": "semantic",
            "llm": copy.deepcopy(llm_config),
        }
    )
    with open(os.path.join(pwd, "../data/test_txt.txt"), "r") as reader:
        content = reader.read()
    chunk = Chunk(id=1, name="test", content=content)

    chunks = splitter.invoke(chunk)
    assert len(chunks) > 0 and isinstance(chunks[0], Chunk)
