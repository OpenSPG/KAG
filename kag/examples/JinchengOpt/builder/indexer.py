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
import kag.builder.component
import kag.builder.default_chain
from kag.builder.runner import BuilderChainStreamRunner
from chain import DefaultUnstructuredDoubleReaderBuilderChain
import kag.common.llm
import kag.common.vectorize_model

logger = logging.getLogger(__name__)


def buildKB(file_path):
    from kag.common.conf import KAG_CONFIG

    runner = BuilderChainStreamRunner.from_config(
        KAG_CONFIG.all_config["kag_builder_pipeline"]
    )
    runner.invoke(file_path)

    logger.info(f"\n\nbuildKB successfully for {file_path}\n\n")


if __name__ == "__main__":
    import_modules_from_path(".")
    buildKB("dt=20250313")

"""
INSERT INTO alifin_jtest_dev.jincheng_doc2x_finance_40w_parsed (content, sourcepath, targetpath)
SELECT content, sourcepath, targetpath 
FROM ant_glm_dev.doc2x_finance_40w_parsed
LIMIT 100
"""
