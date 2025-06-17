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


from kag.builder.runner import BuilderChainStreamRunner
from kag.common.conf import KAGConfigAccessor
import logging

from ruamel.yaml import YAML

yaml = YAML()
yaml.default_flow_style = False
yaml.indent(mapping=2, sequence=4, offset=2)
logger = logging.getLogger(__name__)


class BuilderMain:
    def __init__(self, config: dict):
        super().__init__()
        self.config = config

    def get_runner(self):
        return BuilderChainStreamRunner.from_config(self.config["kag_builder_pipeline"])

    def invoke(self, file_path="placeholder"):
        runner = self.get_runner()
        runner.invoke(file_path)
        logger.info(f"\n\nbuildKB successfully for {file_path}\n\n")


if __name__ == "__main__":

    builder_main = BuilderMain(KAGConfigAccessor.get_config().all_config)
    builder_main.invoke("dt=20250225")
