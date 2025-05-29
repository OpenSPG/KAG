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
import argparse
import logging
import asyncio
import time
from kag.common.registry import Functor
from kag.interface import LLMClient
from kag.builder.runner import BuilderChainRunner

logger = logging.getLogger(__name__)


@Functor.register("benchmark_builder_2wiki")
def index_builder(file_path):
    start = time.time()
    from kag.common.conf import KAG_CONFIG

    runner = BuilderChainRunner.from_config(
        KAG_CONFIG.all_config["kag_builder_pipeline"]
    )
    asyncio.run(runner.ainvoke(file_path))
    end = time.time()
    token_meter = LLMClient.get_token_meter()
    stat = token_meter.to_dict()
    logger.info(
        f"\n\nbuildKB successfully for {file_path}\n\nTimes cost:{end-start}s\n\nTokens cost: {stat}"
    )
    return {"time_cost": end - start, "token_cost": stat}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="args")
    parser.add_argument(
        "--corpus_file",
        type=str,
        help="test file name in /data",
        default="data/sub_corpus.json",
    )

    args = parser.parse_args()
    file_path = args.corpus_file

    # dir_path = os.path.dirname(__file__)
    # file_path = os.path.join(dir_path, file_path)

    index_builder(file_path)
