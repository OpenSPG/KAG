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
import copy
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.builder.runner import BuilderChainRunner


class PDFDemo:
    def __init__(self):
        self.runner = BuilderChainRunner.from_config(
            KAG_CONFIG.all_config["kag_builder_pipeline"]
        )

    def index(self, file_path):
        self.runner.invoke(file_path)


if __name__ == "__main__":
    indexer = PDFDemo()
    dir_path = os.path.dirname(__file__)
    indexer.index(os.path.join(dir_path, "data"))
