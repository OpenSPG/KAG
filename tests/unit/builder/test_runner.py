# -*- coding: utf-8 -*-
import os
import asyncio
from kag.common.conf import KAG_CONFIG
from kag.builder.runner import BuilderChainRunner

pwd = os.path.dirname(__file__)


def test_chain_runner():
    runner_config = {
        "scanner": {"type": "file"},
        "chain": {
            "type": "unstructured",
            "extractor": {
                "type": "schema_free",
                "llm": KAG_CONFIG.all_config["llm"],
            },
            "reader": {"type": "txt"},
            "splitter": {
                "type": "length",
                "split_length": 2000,
                "window_length": 0,
            },
            "vectorizer": KAG_CONFIG.all_config["vectorizer"],
        },
    }
    runner = BuilderChainRunner.from_config(runner_config)
    runner.invoke(os.path.join(pwd, "data/test_txt.txt"))


async def atest_chain_runner():
    runner_config = {
        "scanner": {"type": "file"},
        "chain": {
            "type": "unstructured",
            "extractor": {
                "type": "schema_free",
                "llm": KAG_CONFIG.all_config["llm"],
            },
            "reader": {"type": "txt"},
            "splitter": {
                "type": "length",
                "split_length": 2000,
                "window_length": 0,
            },
            "vectorizer": KAG_CONFIG.all_config["vectorizer"],
        },
    }
    runner = BuilderChainRunner.from_config(runner_config)
    await runner.ainvoke(os.path.join(pwd, "data/test_txt.txt"))


def test_async_chain_runner():
    asyncio.run(atest_chain_runner())


test_async_chain_runner()
