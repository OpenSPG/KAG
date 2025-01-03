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
]
