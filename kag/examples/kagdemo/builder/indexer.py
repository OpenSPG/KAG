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

from kag.builder.component.reader import DocxReader, PDFReader
from kag.builder.component.splitter import LengthSplitter, OutlineSplitter
from kag.builder.component.extractor import KAGExtractor
from kag.builder.component.writer import KGWriter
from kag.solver.logic.solver_pipeline import SolverPipeline
import logging
from kag.common.env import init_kag_config


logger = logging.getLogger(__name__)

file_path = os.path.dirname(__file__)


from kag.builder.default_chain import DefaultUnstructuredBuilderChain
    
def buildKG(test_file,**kwargs):
    chain = DefaultUnstructuredBuilderChain(file_path = test_file)
    chain.invoke(test_file, max_workers=10)
    

if __name__ == "__main__":
    init_kag_config(os.path.join(file_path,"../kag_config.cfg"))
    test_pdf = os.path.join(file_path,"data/KnowledgeGraphTutorialSub.pdf")
    buildKG(test_pdf)