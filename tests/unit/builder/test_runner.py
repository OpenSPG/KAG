# -*- coding: utf-8 -*-
import os
from kag.common.conf import KAG_CONFIG
from kag.builder.runner import BuilderChainRunner

pwd = os.path.dirname(__file__)


def test_chain_runner():
    runner_config = {
        "scanner": {"type": "dir", "file_pattern": ".*long_text.*"},
        "chain": {
            "type": "unstructured",
            "extractor": {
                "type": "schema_free",
                "llm": KAG_CONFIG.all_config["llm"],
            },
            "reader": {"type": "txt"},
            "splitter": {
                "type": "length",
                "split_length": 200,
                "window_length": 0,
            },
            "vectorizer": KAG_CONFIG.all_config["vectorizer"],
            "writer": {"type": "kg"},
        },
        "num_chains": 2,
        "num_threads_per_chain": 4,
    }
    runner = BuilderChainRunner.from_config(runner_config)
    runner.invoke(os.path.join(pwd, "data/"))


test_chain_runner()
