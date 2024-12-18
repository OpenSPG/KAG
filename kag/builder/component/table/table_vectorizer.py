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

from typing import List

from knext.common.base.runnable import Input, Output
from kag.builder.component.vectorizer.batch_vectorizer import BatchVectorizer
from knext.schema.client import SchemaClient


class TableBatchVectorizer(BatchVectorizer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._table_vec_meta()

    def _table_vec_meta(self):
        # schema_client = SchemaClient(project_id=self.project_id)
        # spg_types = schema_client.load()
        self.vec_meta["Table"].append(self._create_vector_field_name("name"))
        self.vec_meta["Table"].append(self._create_vector_field_name("desc"))
        self.vec_meta["TableMetric"].append(self._create_vector_field_name("name"))
        self.vec_meta["MetricConstraint"].append(self._create_vector_field_name("name"))

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        return super().invoke(input=input, **kwargs)
