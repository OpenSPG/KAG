# -*- coding: utf-8 -*-
import os
from kag.common.conf import KAG_CONFIG
from kag.builder.runner import CKPT, BuilderChainRunner

# pwd = os.path.dirname(__file__)
pwd = "./"


def test_ckpt():
    ckpt = CKPT("./")
    ckpt.open()
    ckpt.add("aaaa", "aaaa", {})
    ckpt.add("bbbb", "bbbb", {"num_nodes": 3})
    ckpt.add("cccc", "cccc", {"num_edges": 6})
    ckpt.close()

    ckpt = CKPT("./")
    assert ckpt.is_processed("aaaa")
    assert ckpt.is_processed("bbbb")
    assert ckpt.is_processed("cccc")


def test_chain_runner():
    runner_config = {
        "reader": {"type": "dir", "file_pattern": ".*long_text.*"},
        "chain": {
            "type": "unstructured",
            "extractor": {
                "type": "kag",
                "llm": KAG_CONFIG.all_config["llm"],
            },
            "parser": {"type": "txt"},
            "splitter": {
                "type": "length",
                "split_length": 200,
                "window_length": 0,
            },
            "vectorizer": KAG_CONFIG.all_config["vectorizer"],
            "post_processor": {"type": "base"},
            "writer": {"type": "kg"},
        },
        "num_parallel": 2,
        "chain_level_num_paralle": 8,
    }
    runner = BuilderChainRunner.from_config(runner_config)
    runner.invoke(os.path.join(pwd, "data/"))
