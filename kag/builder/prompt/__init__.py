# -*- coding: utf-8 -*-
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
from kag.builder.prompt.default.knowledge_unit import KnowledgeUnitPrompt
from kag.builder.prompt.default.knowledge_unit_ner import OpenIENERKnowledgeUnitPrompt
from kag.builder.prompt.default.knowledge_unit_triple import (
    OpenIEKnowledgeUnitTriplePrompt,
)
from kag.builder.prompt.default.ner import OpenIENERPrompt as DefaultOpenIENERPrompt
from kag.builder.prompt.default.std import (
    OpenIEEntitystandardizationdPrompt as DefaultOpenIEEntitystandardizationdPrompt,
)
from kag.builder.prompt.default.triple import (
    OpenIETriplePrompt as DefaultOpenIETriplePrompt,
)

from kag.builder.prompt.medical.ner import OpenIENERPrompt as MedicalOpenIENERPrompt
from kag.builder.prompt.medical.std import (
    OpenIEEntitystandardizationdPrompt as MedicalOpenIEEntitystandardizationdPrompt,
)
from kag.builder.prompt.medical.triple import (
    OpenIETriplePrompt as MedicalOpenIETriplePrompt,
)

from kag.builder.prompt.analyze_table_prompt import AnalyzeTablePrompt
from kag.builder.prompt.spg_prompt import SPGPrompt, SPGEntityPrompt, SPGEventPrompt
from kag.builder.prompt.semantic_seg_prompt import SemanticSegPrompt
from kag.builder.prompt.outline_prompt import OutlinePrompt
from kag.builder.prompt.chunk_summary_prompt import ChunkSummaryPrompt

from kag.builder.prompt.table.table_context import TableContextPrompt
from kag.builder.prompt.table.table_row_col_summary import TableRowColSummaryPrompt
from kag.builder.prompt.atomic_query_extract_prompt import AtomicQueryExtractPrompt

__all__ = [
    "DefaultOpenIENERPrompt",
    "DefaultOpenIEEntitystandardizationdPrompt",
    "DefaultOpenIETriplePrompt",
    "MedicalOpenIENERPrompt",
    "MedicalOpenIEEntitystandardizationdPrompt",
    "MedicalOpenIETriplePrompt",
    "AnalyzeTablePrompt",
    "OutlinePrompt",
    "SemanticSegPrompt",
    "SPGPrompt",
    "SPGEntityPrompt",
    "SPGEventPrompt",
    "TableContextPrompt",
    "TableRowColSummaryPrompt",
    "AtomicQueryExtractPrompt",
    "KnowledgeUnitPrompt",
    "OpenIENERKnowledgeUnitPrompt",
    "OpenIEKnowledgeUnitTriplePrompt",
]
