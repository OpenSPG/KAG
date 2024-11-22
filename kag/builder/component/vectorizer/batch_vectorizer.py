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
from collections import defaultdict
from typing import List

from kag.builder.model.sub_graph import SubGraph
from kag.common.conf import KAG_PROJECT_CONF

from kag.common.utils import get_vector_field_name
from kag.interface import VectorizerABC, VectorizeModelABC
from knext.schema.client import SchemaClient
from knext.schema.model.base import IndexTypeEnum
from knext.common.base.runnable import Input, Output


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

    def get_placeholder(self, properties, vector_field):
        for property_key, property_value in properties.items():
            field_name = get_vector_field_name(property_key)
            if field_name != vector_field:
                continue
            if not property_value:
                return None
            if not isinstance(property_value, str):
                message = f"property {property_key!r} must be string to generate embedding vector, got {property_value} with type {type(property_value)}"
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

    def _generate_vectors(self, vectorizer, text_batch, batch_size=1024):
        texts = list(text_batch)
        if not texts:
            return []

        n_batchs = len(texts) // batch_size + 1
        embeddings = []
        for idx in range(n_batchs):
            start = idx * batch_size
            end = min(start + batch_size, len(texts))
            embeddings.extend(vectorizer.vectorize(texts[start:end]))
        return embeddings

    def _fill_vectors(self, vectors, text_batch):
        for vector, (_text, placeholders) in zip(vectors, text_batch.items()):
            for placeholder in placeholders:
                placeholder._embedding_vector = vector

    def batch_generate(self, vectorizer, batch_size=1024):
        text_batch = self._get_text_batch()
        vectors = self._generate_vectors(vectorizer, text_batch, batch_size)
        self._fill_vectors(vectors, text_batch)

    def patch(self):
        for placeholder in self._placeholders:
            placeholder.replace()


class EmbeddingVectorGenerator(object):
    def __init__(self, vectorizer, vector_index_meta=None, extra_labels=("Entity",)):
        self._vectorizer = vectorizer
        self._extra_labels = extra_labels
        self._vector_index_meta = vector_index_meta or {}

    def batch_generate(self, node_batch, batch_size=1024):
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
        manager.batch_generate(self._vectorizer, batch_size)
        manager.patch()


@VectorizerABC.register("batch")
class BatchVectorizer(VectorizerABC):
    def __init__(self, vectorize_model: VectorizeModelABC, batch_size: int = 1024):
        super().__init__()
        self.project_id = KAG_PROJECT_CONF.project_id
        # self._init_graph_store()
        self.vec_meta = self._init_vec_meta()
        self.vectorize_model = vectorize_model
        self.batch_size = batch_size

    def _init_vec_meta(self):
        vec_meta = defaultdict(list)
        schema_client = SchemaClient(project_id=self.project_id)
        spg_types = schema_client.load()
        for type_name, spg_type in spg_types.items():
            for prop_name, prop in spg_type.properties.items():
                if prop_name == "name" or prop.index_type in [
                    IndexTypeEnum.Vector,
                    IndexTypeEnum.TextAndVector,
                ]:
                    vec_meta[type_name].append(get_vector_field_name(prop_name))
        return vec_meta

    def _generate_embedding_vectors(self, input_subgraph: SubGraph) -> SubGraph:
        node_list = []
        node_batch = []
        for node in input_subgraph.nodes:
            if not node.id or not node.name:
                continue
            properties = {"id": node.id, "name": node.name}
            properties.update(node.properties)
            node_list.append((node, properties))
            node_batch.append((node.label, properties.copy()))
        generator = EmbeddingVectorGenerator(self.vectorize_model, self.vec_meta)
        generator.batch_generate(node_batch, self.batch_size)
        for (node, properties), (_node_label, new_properties) in zip(
            node_list, node_batch
        ):
            for key, value in properties.items():
                if key in new_properties and new_properties[key] == value:
                    del new_properties[key]
            node.properties.update(new_properties)
        return input_subgraph

    def invoke(self, input_subgraph: Input, **kwargs) -> List[Output]:
        modified_input = self._generate_embedding_vectors(input_subgraph)
        return [modified_input]
