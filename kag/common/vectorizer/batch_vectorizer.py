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


class Neo4jEmbeddingVectorPlaceholder(object):
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


class Neo4jEmbeddingVectorManager(object):
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
            placeholder = Neo4jEmbeddingVectorPlaceholder(
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
        vectors = vectorizer.vectorize(texts)
        return vectors

    def _fill_vectors(self, vectors, text_batch):
        for vector, (_text, placeholders) in zip(vectors, text_batch.items()):
            for placeholder in placeholders:
                placeholder._embedding_vector = vector

    def batch_vectorize(self, vectorizer):
        text_batch = self._get_text_batch()
        vectors = self._generate_vectors(vectorizer, text_batch)
        self._fill_vectors(vectors, text_batch)

    def patch(self):
        for placeholder in self._placeholders:
            placeholder.replace()


class Neo4jBatchVectorizer(object):
    def __init__(self, vectorizer, vector_index_meta=None, extra_labels=("Entity",)):
        self._vectorizer = vectorizer
        self._extra_labels = extra_labels
        self._vector_index_meta = vector_index_meta or {}

    def batch_vectorize(self, node_batch):
        manager = Neo4jEmbeddingVectorManager()
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
        manager.batch_vectorize(self._vectorizer)
        manager.patch()
