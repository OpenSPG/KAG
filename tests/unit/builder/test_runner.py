# -*- coding: utf-8 -*-
import os
from kag.common.conf import KAG_CONFIG
from kag.builder.runner import BuilderChainRunner

pwd = os.path.dirname(__file__)


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
