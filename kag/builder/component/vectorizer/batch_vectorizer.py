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
import os
from collections import defaultdict
from typing import List

from kag.builder.model.sub_graph import SubGraph
from knext.common.base.runnable import Input, Output
from kag.common.vectorizer import Vectorizer, Neo4jBatchVectorizer
from kag.interface.builder.vectorizer_abc import VectorizerABC
from knext.schema.client import SchemaClient
from knext.project.client import ProjectClient
from knext.schema.model.base import IndexTypeEnum


class BatchVectorizer(VectorizerABC):

    def __init__(self, project_id: str = None, **kwargs):
        super().__init__(**kwargs)
        self.project_id = project_id or os.getenv("KAG_PROJECT_ID")
        self._init_graph_store()
        self.vec_meta = self._init_vec_meta()
        self.vectorizer = Vectorizer.from_config(self.vectorizer_config)

    def _init_graph_store(self):
        """
        Initializes the Graph Store client.

        This method retrieves the graph store configuration from environment variables and the project ID.
        It then fetches the project configuration using the project ID and updates the graph store configuration
        with any additional settings from the project. Finally, it creates and initializes the graph store client
        using the updated configuration.

        Args:
            project_id (str): The id of project.

        Returns:
            GraphStore
        """
        graph_store_config = eval(os.getenv("KAG_GRAPH_STORE", "{}"))
        vectorizer_config = eval(os.getenv("KAG_VECTORIZER", "{}"))
        config = ProjectClient().get_config(self.project_id)
        graph_store_config.update(config.get("graph_store", {}))
        vectorizer_config.update(config.get("vectorizer", {}))
        self.vectorizer_config = vectorizer_config

    def _init_vec_meta(self):
        vec_meta = defaultdict(list)
        schema_client = SchemaClient(project_id=self.project_id)
        spg_types = schema_client.load()
        for type_name, spg_type in spg_types.items():
            for prop_name, prop in spg_type.properties.items():
                if prop_name == "name" or prop.index_type in [IndexTypeEnum.Vector, IndexTypeEnum.TextAndVector]:
                    vec_meta[type_name].append(self._create_vector_field_name(prop_name))
        return vec_meta

    def _create_vector_field_name(self, property_key):
        from kag.common.utils import to_snake_case

        name = f"{property_key}_vector"
        name = to_snake_case(name)
        return "_" + name

    def _neo4j_batch_vectorize(self, vectorizer: Vectorizer, input: SubGraph) -> SubGraph:
        node_list = []
        node_batch = []
        for node in input.nodes:
            if not node.id or not node.name:
                continue
            properties = {"id": node.id, "name": node.name}
            properties.update(node.properties)
            node_list.append((node, properties))
            node_batch.append((node.label, properties.copy()))
        batch_vectorizer = Neo4jBatchVectorizer(vectorizer, self.vec_meta)
        batch_vectorizer.batch_vectorize(node_batch)
        for (node, properties), (_node_label, new_properties) in zip(
            node_list, node_batch
        ):
            for key, value in properties.items():
                if key in new_properties and new_properties[key] == value:
                    del new_properties[key]
            node.properties.update(new_properties)
        return input

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        modified_input = self._neo4j_batch_vectorize(self.vectorizer, input)
        return [modified_input]
