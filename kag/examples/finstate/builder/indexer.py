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
from kag.builder.default_table_chain import DefaultUnstructuredTableBuilderChain
from kag.builder.default_chain import DefaultUnstructuredBuilderChain

from kag.examples.finstate.builder.graph_db_tools import clear_neo4j_data

if __name__ == "__main__":
    clear_neo4j_data("finstate")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    # file_path = os.path.join(current_dir, "data", "差旅管理办法.md")
    # file_path = os.path.join(current_dir, "data", "中芯国际财报2024_3.pdf.md")
    file_path = os.path.join(current_dir, "data", "阿里巴巴2025财年度中期报告.md")
    #file_path = os.path.join(current_dir, "data", "阿里巴巴2025财年度中期报告-1.md")
    DefaultUnstructuredTableBuilderChain().invoke(file_path=file_path, max_workers=1)
    # DefaultUnstructuredBuilderChain().invoke(
    #     file_path=file_path, with_table=False, max_workers=20
    # )