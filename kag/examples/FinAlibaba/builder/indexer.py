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
import os
import logging
import asyncio
from kag.common.registry import import_modules_from_path

from kag.builder.runner import BuilderChainRunner

logger = logging.getLogger(__name__)


async def buildKB(file_path):
    from kag.common.conf import KAG_CONFIG

    runner = BuilderChainRunner.from_config(
        KAG_CONFIG.all_config["kag_builder_pipeline"]
    )
    await runner.ainvoke(file_path)

    logger.info(f"\n\nbuildKB successfully for {file_path}\n\n")


if __name__ == "__main__":
    import_modules_from_path(".")
    dir = os.path.dirname(__file__)
    file_path = os.path.join(dir, "data/alibaba.md")
    asyncio.run(buildKB(file_path))
