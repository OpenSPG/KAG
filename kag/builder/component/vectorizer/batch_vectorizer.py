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
import asyncio
from collections import defaultdict
from typing import List, Optional
from tenacity import stop_after_attempt, retry

from kag.builder.model.sub_graph import SubGraph

from kag.common.utils import get_vector_field_name, get_sparse_vector_field_name
from kag.interface import VectorizerABC, VectorizeModelABC, SparseVectorizeModelABC
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
            self._properties[self._property_key] = self._property_value
            self._properties[self._vector_field] = self._embedding_vector

    def __repr__(self):
        return repr(self._number)


class EmbeddingVectorManager(object):
    def __init__(self, disable_generation=None):
        self._dense_placeholders = []
        self._sparse_placeholders = []
        self._disable_generation = frozenset(disable_generation or [])

    def get_dense_placeholder(self, label, properties, vector_field):
        for property_key, property_value in properties.items():
            disable_prop_key = f"{label}.{property_key}"
            if disable_prop_key in self._disable_generation:
                continue
            field_name = get_vector_field_name(property_key)
            if field_name != vector_field:
                continue
            if property_value is None or property_value == "":
                return None
            if not isinstance(property_value, str):
                property_value = str(property_value)
            num = len(self._dense_placeholders)
            placeholder = EmbeddingVectorPlaceholder(
                num, properties, vector_field, property_key, property_value
            )
            self._dense_placeholders.append(placeholder)
            return placeholder
        return None

    def get_sparse_placeholder(self, label, properties, vector_field):
        for property_key, property_value in properties.items():
            disable_prop_key = f"{label}.{property_key}"
            if disable_prop_key in self._disable_generation:
                continue
            field_name = get_sparse_vector_field_name(property_key)
            if field_name != vector_field:
                continue
            if property_value is None or property_value == "":
                return None
            if not isinstance(property_value, str):
                property_value = str(property_value)
            num = len(self._sparse_placeholders)
            placeholder = EmbeddingVectorPlaceholder(
                num, properties, vector_field, property_key, property_value
            )
            self._sparse_placeholders.append(placeholder)
            return placeholder
        return None

    def _get_dense_text_batch(self):
        text_batch = dict()
        for placeholder in self._dense_placeholders:
            property_value = placeholder._property_value
            if property_value not in text_batch:
                text_batch[property_value] = list()
            text_batch[property_value].append(placeholder)
        return text_batch

    def _get_sparse_text_batch(self):
        text_batch = dict()
        for placeholder in self._sparse_placeholders:
            property_value = placeholder._property_value
            if property_value not in text_batch:
                text_batch[property_value] = list()
            text_batch[property_value].append(placeholder)
        return text_batch

    def _generate_dense_vectors(self, dense_vectorizer, text_batch, batch_size=32):
        texts = list(text_batch)
        if not texts:
            return []

        if len(texts) % batch_size == 0:
            n_batchs = len(texts) // batch_size
        else:
            n_batchs = len(texts) // batch_size + 1
        embeddings = []
        for idx in range(n_batchs):
            start = idx * batch_size
            end = min(start + batch_size, len(texts))
            sub_texts = []
            for text in texts[start:end]:
                if text.strip() != "":
                    sub_texts.append(text)
                else:
                    sub_texts.append("none")
            if len(sub_texts) == 0:
                continue
            embeddings.extend(dense_vectorizer.vectorize(sub_texts))
        return embeddings

    def _generate_sparse_vectors(self, sparse_vectorizer, text_batch, batch_size=32):
        texts = list(text_batch)
        if not texts:
            return []

        if len(texts) % batch_size == 0:
            n_batchs = len(texts) // batch_size
        else:
            n_batchs = len(texts) // batch_size + 1
        embeddings = []
        for idx in range(n_batchs):
            start = idx * batch_size
            end = min(start + batch_size, len(texts))
            sub_texts = []
            for text in texts[start:end]:
                if text.strip() != "":
                    sub_texts.append(text)
                else:
                    sub_texts.append("none")
            if len(sub_texts) == 0:
                continue
            embeddings.extend(sparse_vectorizer.vectorize(sub_texts))
        return embeddings

    async def _agenerate_dense_vectors(
        self, dense_vectorizer, text_batch, batch_size=32
    ):
        texts = list(text_batch)
        if not texts:
            return []

        if len(texts) % batch_size == 0:
            n_batchs = len(texts) // batch_size
        else:
            n_batchs = len(texts) // batch_size + 1
        tasks = []
        for idx in range(n_batchs):
            start = idx * batch_size
            end = min(start + batch_size, len(texts))
            sub_texts = []
            for text in texts[start:end]:
                if text.strip() != "":
                    sub_texts.append(text)
                else:
                    sub_texts.append("none")
            if len(sub_texts) == 0:
                continue
            tasks.append(
                asyncio.create_task(dense_vectorizer.avectorize(texts[start:end]))
            )
        results = await asyncio.gather(*tasks)
        return [item for sublist in results for item in sublist]

    async def _agenerate_sparse_vectors(
        self, sparse_vectorizer, text_batch, batch_size=32
    ):
        texts = list(text_batch)
        if not texts:
            return []

        if len(texts) % batch_size == 0:
            n_batchs = len(texts) // batch_size
        else:
            n_batchs = len(texts) // batch_size + 1
        tasks = []
        for idx in range(n_batchs):
            start = idx * batch_size
            end = min(start + batch_size, len(texts))
            sub_texts = []
            for text in texts[start:end]:
                if text.strip() != "":
                    sub_texts.append(text)
                else:
                    sub_texts.append("none")
            if len(sub_texts) == 0:
                continue
            tasks.append(
                asyncio.create_task(sparse_vectorizer.avectorize(texts[start:end]))
            )
        results = await asyncio.gather(*tasks)
        return [item for sublist in results for item in sublist]

    def _fill_vectors(self, vectors, text_batch):
        for vector, (_text, placeholders) in zip(vectors, text_batch.items()):
            for placeholder in placeholders:
                placeholder._embedding_vector = vector

    def batch_generate_dense(self, dense_vectorizer, batch_size=32):
        text_batch = self._get_dense_text_batch()
        vectors = self._generate_dense_vectors(dense_vectorizer, text_batch, batch_size)
        self._fill_vectors(vectors, text_batch)

    def batch_generate_sparse(self, sparse_vectorizer, batch_size=32):
        text_batch = self._get_sparse_text_batch()
        vectors = self._generate_sparse_vectors(
            sparse_vectorizer, text_batch, batch_size
        )
        self._fill_vectors(vectors, text_batch)

    async def abatch_generate_dense(self, dense_vectorizer, batch_size=32):
        text_batch = self._get_dense_text_batch()
        vectors = await self._agenerate_dense_vectors(
            dense_vectorizer, text_batch, batch_size
        )
        self._fill_vectors(vectors, text_batch)

    async def abatch_generate_sparse(self, sparse_vectorizer, batch_size=32):
        text_batch = self._get_sparse_text_batch()
        vectors = await self._agenerate_sparse_vectors(
            sparse_vectorizer, text_batch, batch_size
        )
        self._fill_vectors(vectors, text_batch)

    def patch(self):
        for placeholder in self._dense_placeholders:
            placeholder.replace()
        for placeholder in self._sparse_placeholders:
            placeholder.replace()


class EmbeddingVectorGenerator(object):
    def __init__(
        self,
        vectorizer,
        vector_index_meta=None,
        disable_generation=None,
        sparse_vectorizer=None,
        extra_labels=("Entity",),
    ):
        self._vectorizer = vectorizer
        self._extra_labels = extra_labels
        self._vector_index_meta = vector_index_meta or ({}, {})
        self._disable_generation = disable_generation
        self._sparse_vectorizer = sparse_vectorizer

    def batch_generate(self, node_batch, batch_size=32):
        manager = EmbeddingVectorManager(self._disable_generation)
        dense_vec_meta, sparse_vec_meta = self._vector_index_meta
        for node_item in node_batch:
            label, properties = node_item
            labels = [label]
            if self._extra_labels:
                labels.extend(self._extra_labels)
            for label in labels:
                if label in dense_vec_meta:
                    for vector_field in dense_vec_meta[label]:
                        if vector_field not in properties:
                            placeholder = manager.get_dense_placeholder(
                                label, properties, vector_field
                            )
                            if placeholder is not None:
                                properties[vector_field] = placeholder
                if label in sparse_vec_meta and self._sparse_vectorizer is not None:
                    for vector_field in sparse_vec_meta[label]:
                        if vector_field not in properties:
                            placeholder = manager.get_sparse_placeholder(
                                label, properties, vector_field
                            )
                            if placeholder is not None:
                                properties[vector_field] = placeholder
        manager.batch_generate_dense(self._vectorizer, batch_size)
        if self._sparse_vectorizer is not None:
            manager.batch_generate_sparse(self._sparse_vectorizer, batch_size)
        manager.patch()

    async def abatch_generate(self, node_batch, batch_size=32):
        manager = EmbeddingVectorManager(self._disable_generation)
        dense_vec_meta, sparse_vec_meta = self._vector_index_meta
        for node_item in node_batch:
            label, properties = node_item
            labels = [label]
            if self._extra_labels:
                labels.extend(self._extra_labels)
            for label in labels:
                if label in dense_vec_meta:
                    for vector_field in dense_vec_meta[label]:
                        if vector_field not in properties:
                            placeholder = manager.get_dense_placeholder(
                                label, properties, vector_field
                            )
                            if placeholder is not None:
                                properties[vector_field] = placeholder
                if label in sparse_vec_meta and self._sparse_vectorizer is not None:
                    for vector_field in sparse_vec_meta[label]:
                        if vector_field not in properties:
                            placeholder = manager.get_sparse_placeholder(
                                label, properties, vector_field
                            )
                            if placeholder is not None:
                                properties[vector_field] = placeholder
        await manager.abatch_generate_dense(self._vectorizer, batch_size)
        if self._sparse_vectorizer is not None:
            await manager.abatch_generate_sparse(self._sparse_vectorizer, batch_size)
        manager.patch()


@VectorizerABC.register("batch")
@VectorizerABC.register("batch_vectorizer")
class BatchVectorizer(VectorizerABC):
    """
    A class for generating embedding vectors for node attributes in a SubGraph in batches.

    This class inherits from VectorizerABC and provides the functionality to generate embedding vectors
    for node attributes in a SubGraph in batches. It uses a specified vectorization model and processes
    the nodes of a specified batch size.

    Attributes:
        project_id (int): The ID of the project associated with the SubGraph.
        vec_meta (defaultdict): Metadata for vector fields in the SubGraph.
        vectorize_model (VectorizeModelABC): The model used for generating embedding vectors.
        batch_size (int): The size of the batches in which to process the nodes.
    """

    def __init__(
        self,
        vectorize_model: VectorizeModelABC,
        batch_size: int = 32,
        disable_generation: Optional[List[str]] = None,
        sparse_vectorize_model: SparseVectorizeModelABC = None,
        **kwargs,
    ):
        """
        Initializes the BatchVectorizer with the specified vectorization model and batch size.

        Args:
            vectorize_model (VectorizeModelABC): The model used for generating embedding vectors.
            batch_size (int): The size of the batches in which to process the nodes. Defaults to 32.
        """
        super().__init__(**kwargs)
        self.project_id = self.kag_project_config.project_id
        # self._init_graph_store()
        self.vec_meta = self._init_vec_meta()
        self.vectorize_model = vectorize_model
        self.sparse_vectorize_model = sparse_vectorize_model
        self.batch_size = batch_size
        self.disable_generation = disable_generation

    def _init_vec_meta(self):
        """
        Initializes the vector metadata for the SubGraph.

        Returns:
            Tuple[defaultdict, defaultdict]: Metadata for dense and sparse vector fields in the SubGraph.
        """
        dense_vec_meta = defaultdict(list)
        sparse_vec_meta = defaultdict(list)
        schema_client = SchemaClient(
            host_addr=self.kag_project_config.host_addr, project_id=self.project_id
        )
        spg_types = schema_client.load()
        for type_name, spg_type in spg_types.items():
            for prop_name, prop in spg_type.properties.items():
                if prop_name == "name" or prop.index_type in [
                    IndexTypeEnum.Vector,
                    IndexTypeEnum.TextAndVector,
                ]:
                    dense_vec_meta[type_name].append(get_vector_field_name(prop_name))
                elif prop.index_type in [
                    IndexTypeEnum.SparseVector,
                    IndexTypeEnum.TextAndSparseVector,
                ]:
                    sparse_vec_meta[type_name].append(
                        get_sparse_vector_field_name(prop_name)
                    )
        vec_meta = dense_vec_meta, sparse_vec_meta
        return vec_meta

    @retry(stop=stop_after_attempt(3), reraise=True)
    def _generate_embedding_vectors(self, input_subgraph: SubGraph) -> SubGraph:
        """
        Generates embedding vectors for the nodes in the input SubGraph.

        Args:
            input_subgraph (SubGraph): The SubGraph for which to generate embedding vectors.

        Returns:
            SubGraph: The modified SubGraph with generated embedding vectors.
        """
        node_list = []
        node_batch = []
        for node in input_subgraph.nodes:
            if not node.id or not node.name:
                continue
            properties = {"id": node.id, "name": node.name}
            properties.update(node.properties)
            node_list.append((node, properties))
            node_batch.append((node.label, properties.copy()))
        generator = EmbeddingVectorGenerator(
            self.vectorize_model,
            self.vec_meta,
            self.disable_generation,
            self.sparse_vectorize_model,
        )
        generator.batch_generate(node_batch, self.batch_size)
        for (node, properties), (_node_label, new_properties) in zip(
            node_list, node_batch
        ):
            for key, value in properties.items():
                if key in new_properties and new_properties[key] == value:
                    del new_properties[key]
            node.properties.update(new_properties)
        return input_subgraph

    @retry(stop=stop_after_attempt(3), reraise=True)
    async def _agenerate_embedding_vectors(self, input_subgraph: SubGraph) -> SubGraph:
        """
        Generates embedding vectors for the nodes in the input SubGraph.

        Args:
            input_subgraph (SubGraph): The SubGraph for which to generate embedding vectors.

        Returns:
            SubGraph: The modified SubGraph with generated embedding vectors.
        """
        node_list = []
        node_batch = []
        for node in input_subgraph.nodes:
            if not node.id or not node.name:
                continue
            properties = {"id": node.id, "name": node.name}
            properties.update(node.properties)
            node_list.append((node, properties))
            node_batch.append((node.label, properties.copy()))
        generator = EmbeddingVectorGenerator(
            self.vectorize_model,
            self.vec_meta,
            self.disable_generation,
            self.sparse_vectorize_model,
        )
        await generator.abatch_generate(node_batch, self.batch_size)
        for (node, properties), (_node_label, new_properties) in zip(
            node_list, node_batch
        ):
            for key, value in properties.items():
                if key in new_properties and new_properties[key] == value:
                    del new_properties[key]
            node.properties.update(new_properties)
        return input_subgraph

    def _invoke(self, input_subgraph: Input, **kwargs) -> List[Output]:
        """
        Invokes the generation of embedding vectors for the input SubGraph.

        Args:
            input_subgraph (Input): The SubGraph for which to generate embedding vectors.
            **kwargs: Additional keyword arguments, currently unused but kept for potential future expansion.

        Returns:
            List[Output]: A list containing the modified SubGraph with generated embedding vectors.
        """
        modified_input = self._generate_embedding_vectors(input_subgraph)
        return [modified_input]

    async def _ainvoke(self, input_subgraph: Input, **kwargs) -> List[Output]:
        """
        Invokes the generation of embedding vectors for the input SubGraph.

        Args:
            input_subgraph (Input): The SubGraph for which to generate embedding vectors.
            **kwargs: Additional keyword arguments, currently unused but kept for potential future expansion.

        Returns:
            List[Output]: A list containing the modified SubGraph with generated embedding vectors.
        """
        modified_input = await self._agenerate_embedding_vectors(input_subgraph)
        return [modified_input]
