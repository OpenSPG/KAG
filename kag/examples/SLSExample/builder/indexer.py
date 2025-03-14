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


import json
from kag.builder.runner import BuilderChainRunner, BuilderChainStreamRunner
from kag.common.conf import KAG_CONFIG
import logging

from ruamel.yaml import YAML

yaml = YAML()
yaml.default_flow_style = False
yaml.indent(mapping=2, sequence=4, offset=2)
logger = logging.getLogger(__name__)


class SLSUnstructuredChain:
    def __init__(self, config_str: str):
        super().__init__()
        self.config = yaml.load(config_str)

    def get_runner(self):
        return BuilderChainStreamRunner.from_config(self.config["kag_builder_pipeline"])

    def buildKB(self, file_path="placeholder"):
        runner = self.get_runner()
        runner.invoke(file_path)

        logger.info(f"\n\nbuildKB successfully for {file_path}\n\n")


if __name__ == "__main__":

    config_str = json.dumps(KAG_CONFIG.all_config)
    sls_chain = SLSUnstructuredChain(config_str)
    sls_chain.buildKB()
