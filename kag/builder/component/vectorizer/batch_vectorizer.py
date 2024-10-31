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
from kag.common.vectorizer import Vectorizer
from kag.interface.builder.vectorizer_abc import VectorizerABC
from knext.schema.client import SchemaClient
from knext.project.client import ProjectClient
from knext.schema.model.base import IndexTypeEnum


class EmbeddingVectorPlaceholder(object):
    def __init__(self, number, properties, vector_field, property_key, property_value):
        self._number = number
        self._properties = properties
        self._vector_field = vector_field
        self._property_key = property_key
        self._property_value = property_value
        self._embedding_vector = None

    def replace(self):
        if self._embedding_vector is not None:
            self._properties[self._vector_field] = self._embedding_vector

    def __repr__(self):
        return repr(self._number)


class EmbeddingVectorManager(object):
    def __init__(self):
        self._placeholders = []

    def _create_vector_field_name(self, property_key):
        from kag.common.utils import to_snake_case

        name = f"{property_key}_vector"
        name = to_snake_case(name)
        return "_" + name

    def get_placeholder(self, properties, vector_field):
        for property_key, property_value in properties.items():
            field_name = self._create_vector_field_name(property_key)
            if field_name != vector_field:
                continue
            if not property_value:
                return None
            if not isinstance(property_value, str):
                message = f"property {property_key!r} must be string to generate embedding vector"
                raise RuntimeError(message)
            num = len(self._placeholders)
            placeholder = EmbeddingVectorPlaceholder(
                num, properties, vector_field, property_key, property_value
            )
            self._placeholders.append(placeholder)
            return placeholder
        return None

    def _get_text_batch(self):
        text_batch = dict()
        for placeholder in self._placeholders:
            property_value = placeholder._property_value
            if property_value not in text_batch:
                text_batch[property_value] = list()
            text_batch[property_value].append(placeholder)
        return text_batch

    def _generate_vectors(self, vectorizer, text_batch):
        texts = list(text_batch)
        if not texts:
            return []
        vectors = vectorizer.vectorize(texts)
        return vectors

    def _fill_vectors(self, vectors, text_batch):
        for vector, (_text, placeholders) in zip(vectors, text_batch.items()):
            for placeholder in placeholders:
                placeholder._embedding_vector = vector

    def batch_generate(self, vectorizer):
        text_batch = self._get_text_batch()
        vectors = self._generate_vectors(vectorizer, text_batch)
        self._fill_vectors(vectors, text_batch)

    def patch(self):
        for placeholder in self._placeholders:
            placeholder.replace()


class EmbeddingVectorGenerator(object):
    def __init__(self, vectorizer, vector_index_meta=None, extra_labels=("Entity",)):
        self._vectorizer = vectorizer
        self._extra_labels = extra_labels
        self._vector_index_meta = vector_index_meta or {}

    def batch_generate(self, node_batch):
        manager = EmbeddingVectorManager()
        vector_index_meta = self._vector_index_meta
        for node_item in node_batch:
            label, properties = node_item
            labels = [label]
            if self._extra_labels:
                labels.extend(self._extra_labels)
            for label in labels:
                if label not in vector_index_meta:
                    continue
                for vector_field in vector_index_meta[label]:
                    if vector_field in properties:
                        continue
                    placeholder = manager.get_placeholder(properties, vector_field)
                    if placeholder is not None:
                        properties[vector_field] = placeholder
        manager.batch_generate(self._vectorizer)
        manager.patch()


class BatchVectorizer(VectorizerABC):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project_id = self.project_id or os.getenv("KAG_PROJECT_ID")
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

    def _generate_embedding_vectors(self, vectorizer: Vectorizer, input: SubGraph) -> SubGraph:
        node_list = []
        node_batch = []
        for node in input.nodes:
            if not node.id or not node.name:
                continue
            properties = {"id": node.id, "name": node.name}
            properties.update(node.properties)
            node_list.append((node, properties))
            node_batch.append((node.label, properties.copy()))
        generator = EmbeddingVectorGenerator(vectorizer, self.vec_meta)
        generator.batch_generate(node_batch)
        for (node, properties), (_node_label, new_properties) in zip(
            node_list, node_batch
        ):
            for key, value in properties.items():
                if key in new_properties and new_properties[key] == value:
                    del new_properties[key]
            node.properties.update(new_properties)
        return input

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        modified_input = self._generate_embedding_vectors(self.vectorizer, input)
        return [modified_input]
