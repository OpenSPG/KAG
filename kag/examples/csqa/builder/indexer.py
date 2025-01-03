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

import os
import logging
from kag.common.registry import import_modules_from_path
from kag.builder.runner import BuilderChainRunner

logger = logging.getLogger(__name__)


def buildKB(dir_path):
    from kag.common.conf import KAG_CONFIG

    runner = BuilderChainRunner.from_config(
        KAG_CONFIG.all_config["kag_builder_pipeline"]
    )
    runner.invoke(dir_path)

    logger.info(f"\n\nbuildKB successfully for {dir_path}\n\n")


if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.abspath(__file__))
    import_modules_from_path(dir_path)

    data_dir_path = os.path.join(dir_path, "data")
    buildKB(data_dir_path)
