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

import asyncio
import os
import logging
import time

from kag.common.registry import import_modules_from_path
from kag.builder.runner import BuilderChainRunner
from kag.interface import LLMClient

logger = logging.getLogger(__name__)


async def buildKB(dir_path):
    from kag.common.conf import KAG_CONFIG

    start = time.time()
    runner = BuilderChainRunner.from_config(
        KAG_CONFIG.all_config["kag_builder_pipeline"]
    )
    await runner.ainvoke(dir_path)
    end = time.time()

    token_meter = LLMClient.get_token_meter()
    stat = token_meter.to_dict()
    logger.info(
        f"\n\nbuildKB successfully for {dir_path}\n\nTimes cost:{end-start}s\n\nTokens cost: {stat}"
    )


def buildKB_debug(dir_path):
    from kag.common.conf import KAG_CONFIG

    runner = BuilderChainRunner.from_config(
        KAG_CONFIG.all_config["kag_builder_pipeline"]
    )
    runner.invoke(dir_path)


if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.dirname(dir_path)
    import_modules_from_path(module_path)

    data_dir_path = os.path.join(dir_path, "data")
    asyncio.run(buildKB(data_dir_path))
    # buildKB_debug(data_dir_path)
