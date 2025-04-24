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
from typing import List, Optional
from kag.builder.component.vectorizer.batch_vectorizer import EmbeddingVectorGenerator
from tenacity import stop_after_attempt, retry

from kag.builder.model.sub_graph import SubGraph
from kag.common.conf import KAG_PROJECT_CONF

from kag.common.utils import get_vector_field_name
from kag.interface import VectorizerABC, VectorizeModelABC
from knext.schema.client import SchemaClient
from knext.schema.model.base import IndexTypeEnum
from knext.common.base.runnable import Input, Output


class AffairBatchVectorizer(VectorizerABC):
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
    ):
        """
        Initializes the BatchVectorizer with the specified vectorization model and batch size.

        Args:
            vectorize_model (VectorizeModelABC): The model used for generating embedding vectors.
            batch_size (int): The size of the batches in which to process the nodes. Defaults to 32.
        """
        super().__init__()
        self.project_id = KAG_PROJECT_CONF.project_id
        # self._init_graph_store()
        self.vec_meta = self._init_vec_meta()
        self.vectorize_model = vectorize_model
        self.batch_size = batch_size
        self.disable_generation = disable_generation

    def _init_vec_meta(self):
        """
        Initializes the vector metadata for the SubGraph.

        Returns:
            defaultdict: Metadata for vector fields in the SubGraph.
        """
        vec_meta = defaultdict(list)
        schema_client = SchemaClient(
            host_addr=KAG_PROJECT_CONF.host_addr, project_id=self.project_id
        )
        spg_types = schema_client.load()
        for type_name, spg_type in spg_types.items():
            for prop_name, prop in spg_type.properties.items():
                if prop.index_type in [
                    IndexTypeEnum.Vector,
                    IndexTypeEnum.TextAndVector,
                ]:
                    vec_meta[type_name].append(get_vector_field_name(prop_name))
        return vec_meta

    @retry(stop=stop_after_attempt(3))
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
            self.vectorize_model, self.vec_meta, self.disable_generation
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
