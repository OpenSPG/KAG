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
import re
import numpy as np
import logging
import torch
import igraph as ig
from typing import Dict, List
from tqdm import tqdm
from threading import Lock

from kag.interface.solver.model.one_hop_graph import (
    EntityData,
    RelationData,
    OneHopGraphData,
    Prop,
)
from kag.common.checkpointer import CheckpointerManager
from kag.common.tools.graph_api.model.table_model import TableData
from knext.schema.client import CHUNK_TYPE

logger = logging.getLogger()


def get_node_unique_id(biz_id, label):
    return f"{biz_id}_{label}"


def configure_device(use_mps=True):
    if torch.cuda.is_available():
        device = "cuda"
    elif (
        use_mps and hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    ):
        device = "mps"
    else:
        device = "cpu"
    logger.debug(f"Using device: {device}")
    return device


class MemoryGraph:
    _instances = {}
    _lock = Lock()
    _dict_lock = Lock()

    def __new__(cls, namespace, ckpt_dir, vectorizer):
        path = ckpt_dir
        with cls._lock:
            if path not in cls._instances:
                instance = super(MemoryGraph, cls).__new__(cls)
                instance._initialize(namespace, ckpt_dir, vectorizer)
                cls._instances[path] = instance
            return cls._instances[path]

    def _initialize(self, namespace, ckpt_dir, vectorizer):
        """
        Initialize the MemoryGraph instance.

        :param namespace: namespace of the memory graph
        :param ckpt_dir: directory of the checkpoint files
        :param vectorizer: vectorizer, to turn strings into vectors
        """
        self.namespace = namespace
        self.ckpt_dir = ckpt_dir
        self.chunk_label = f"{self.namespace}.{CHUNK_TYPE}"
        self._vectorizer = vectorizer
        self._emb_cache = {}
        self.from_ckpt()

    def from_ckpt(self):
        self.name2id = {}
        self.id2name = {}
        self.chunk_ids = set()
        self.entity_ids = set()

        graph_pickle = os.path.join(self.ckpt_dir, "graph")
        if os.path.isfile(graph_pickle):
            self._backend_graph = ig.Graph.Read(graph_pickle, "picklez")
            for idx in range(self._backend_graph.vcount()):
                node = self._backend_graph.vs[idx]
                unique_id = get_node_unique_id(node.id, node.label)
                self.name2id[unique_id] = idx
                self.id2name[idx] = unique_id
                if node["label"] == self.chunk_label:
                    self.chunk_ids.add(idx)
                else:
                    self.entity_ids.add(idx)
            return
        else:
            self._backend_graph = ig.Graph(directed=False)

        checkpointer = CheckpointerManager.get_checkpointer(
            {
                "type": "diskcache",
                "ckpt_dir": self.ckpt_dir,
                "rank": 0,
                "world_size": 1,
            }
        )
        print("Loading graph from checkpoint...")
        keys = checkpointer.keys()
        node_attr_map = {}
        edge_map = {}
        n_nodes = 0
        n_edges = 0
        for k in tqdm(
            keys,
            total=len(keys),
            desc="Loading Nodes",
            position=0,
        ):
            graphs = checkpointer.read_from_ckpt(k)
            for graph in graphs:
                for node in graph.nodes:
                    unique_id = get_node_unique_id(node.id, node.label)
                    if unique_id not in self.name2id:
                        self.name2id[unique_id] = n_nodes
                        self.id2name[n_nodes] = unique_id
                        node_attr_map[unique_id] = node
                        if node.label == self.chunk_label:
                            self.chunk_ids.add(n_nodes)
                        else:
                            self.entity_ids.add(n_nodes)
                        n_nodes += 1

        for k in tqdm(
            keys,
            total=len(keys),
            desc="Loading Edges",
            position=0,
        ):
            graphs = checkpointer.read_from_ckpt(k)
            for graph in graphs:
                for edge in graph.edges:
                    from_unique_id = get_node_unique_id(edge.from_id, edge.from_type)
                    to_unique_id = get_node_unique_id(edge.to_id, edge.to_type)
                    if from_unique_id in self.name2id and to_unique_id in self.name2id:
                        edge_map[n_edges] = (
                            (
                                self.name2id[from_unique_id],
                                self.name2id[to_unique_id],
                            ),
                            edge,
                        )
                        n_edges += 1

        print(f"there are {len(self.name2id)} nodes and {len(edge_map)} edges")

        self._backend_graph.add_vertices(len(self.name2id))
        for node_key, node in tqdm(
            node_attr_map.items(),
            total=len(node_attr_map),
            desc="Loading Node Attr",
            position=0,
        ):
            node_index = self.name2id[node_key]
            self._backend_graph.vs[node_index].update_attributes(
                node.properties,
                id=node.id,
                name=node.name,
                label=node.label,
            )

        edges = []
        for idx in range(n_edges):
            edges.append(edge_map[idx][0])
        self._backend_graph.add_edges(edges)
        for idx in range(n_edges):
            edge = self._backend_graph.es[idx]
            a = edge_map[idx][1]
            edge.update_attributes(
                a.properties,
                id=a.id,
                label=a.label,
                from_id=a.from_id,
                from_type=a.from_type,
                to_id=a.to_id,
                to_type=a.to_type,
            )

        CheckpointerManager.close()

    def get_entity(self, biz_id, label, **kwargs) -> EntityData:
        """
        Get data of the specified entity.

        :param biz_id: entity business id。
        :param label: entity label
        :return: data of the specified entity
        """
        vertex = self._get_vertex(biz_id, label)
        entity = self._create_entity_from_vertex(vertex, biz_id, label)
        return entity

    def get_one_hop_graph(self, biz_id, label) -> OneHopGraphData:
        """
        Get one-hop graph of the specified entity.

        :param biz_id: entity business id。
        :param label: entity label
        :return: one-hop graph of the specified entity
        """
        start_vertex = self._get_vertex(biz_id, label)
        start_entity = self._create_entity_from_vertex(start_vertex, biz_id, label)
        one_hop = OneHopGraphData(None, "s")
        one_hop.s = start_entity
        in_edges = start_vertex.in_edges()
        for in_edge in in_edges:
            source_entity = self._create_entity_from_vertex(in_edge.source_vertex)
            in_relation = self._create_relation_from_edge(
                in_edge, source_entity, start_entity
            )
            one_hop.in_relations.setdefault(in_relation.type, []).append(in_relation)
        out_edges = start_vertex.out_edges()
        for out_edge in out_edges:
            target_entity = self._create_entity_from_vertex(out_edge.target_vertex)
            out_relation = self._create_relation_from_edge(
                out_edge, start_entity, target_entity
            )
            one_hop.out_relations.setdefault(out_relation.type, []).append(out_relation)
        return one_hop

    def _get_vertex(self, biz_id, label):
        unique_id = get_node_unique_id(biz_id, label)
        if unique_id not in self.name2id:
            raise ValueError(f"no such entity {label} {biz_id}")
        return self._backend_graph.vs[self.name2id[unique_id]]

    @staticmethod
    def _create_entity_from_vertex(vertex, biz_id=None, label=None) -> EntityData:
        attributes = vertex.attributes()
        entity = EntityData()
        entity.prop = Prop.from_dict(attributes, None, None)
        entity.biz_id = attributes.get("id", biz_id)
        entity.name = attributes.get("name", "")
        entity.description = attributes.get(
            "content", attributes.get("description", attributes.get("desc", ""))
        )
        entity.type = attributes.get("label", label)
        entity.name_vec = attributes.get("_name_vector")
        entity.content_vec = attributes.get("_content_vector")
        entity.type_zh = None
        entity.score = 1.0
        return entity

    @staticmethod
    def _create_relation_from_edge(
        edge, from_entity: EntityData, end_entity: EntityData
    ) -> RelationData:
        attributes = edge.attributes()
        relation = RelationData()
        relation.prop = Prop.from_dict(attributes, None, None)
        relation.from_id = from_entity.biz_id
        relation.end_id = end_entity.biz_id
        relation.from_entity = from_entity
        relation.from_type = from_entity.type
        relation.from_alias = "s"
        relation.end_type = end_entity.type
        relation.end_entity = end_entity
        relation.end_alias = "o"
        relation.type = attributes.get("label")
        relation.type_zh = None
        return relation

    def execute_dsl(self, dsl, **kwargs) -> TableData:
        """
        Execute DSL query statement.

        :param dsl: the query statement
        :param kwargs: other optional arguments
        :return: query result data as TableData
        """
        raise NotImplementedError

    def named_entity_recognition(self, query: str):
        output = []
        query = query.lower()
        for idx in self.entity_ids:
            node = self._backend_graph.vs[idx]
            if len(node["name"]) > 8 and node["name"].lower() in query:
                output.append(node["name"])
        return output

    def calculate_pagerank_scores(self, start_nodes: List[Dict], **kwargs) -> Dict:
        """
        Calculate PageRank scores.

        :param target_vertex_type: target vertex type (not used currently)
        :param start_nodes: list of start nodes; a start node is a dictionary (not used currently)
        :param kwargs: other optional arguments
        :return: result as a dictionary mapping node ids to scores
        """
        reset_prob = np.zeros(self._backend_graph.vcount())
        for start_node in start_nodes:
            node_biz_id = start_node.get("id", start_node.get("name"))
            if "type" in start_node.keys():
                node_type = start_node["type"]
            elif "__labels__" in start_node.keys():
                labels = start_node["__labels__"]
                node_type = None
                for label in labels:
                    if label == "Entity":
                        continue
                    node_type = label
                    break
            else:
                node_type = None
            if node_type is not None:
                node_unique_id = get_node_unique_id(node_biz_id, node_type)
            else:
                continue
            if node_unique_id not in self.name2id:
                logger.warning(f"{node_unique_id} not found")
                continue
            node_id = self.name2id[node_unique_id]
            reset_prob[node_id] = 1
        scores = self._backend_graph.personalized_pagerank(
            vertices=range(self._backend_graph.vcount()),
            damping=kwargs.get("damping", 0.1),
            directed=False,
            reset=reset_prob,
            implementation="prpack",
        )
        return scores

    def ppr_chunk_retrieval(self, start_nodes, topk=10, **kwargs):
        try:
            ppr_scores = np.array(self.calculate_pagerank_scores(start_nodes, **kwargs))

            mask = np.ones(self._backend_graph.vcount()) * (-float("inf"))
            for chunk_id in self.chunk_ids:
                mask[chunk_id] = 0
            ppr_scores = ppr_scores + mask
            topk = min(topk, len(self.chunk_ids))
            top_indices = np.argsort(ppr_scores)[-topk:]
            output = []
            for idx in top_indices[::-1]:
                node_attributes = self._backend_graph.vs[idx].attributes()
                node_attributes["__labels__"] = [node_attributes["label"]]
                output.append(
                    {
                        "score": ppr_scores[idx],
                        "node": node_attributes,
                    }
                )
            return output
        except:
            logger.info(
                f"Failed to run PPR chunk retrieval return [], input={start_nodes}",
                exc_info=True,
            )
            return []

    def dpr_chunk_retrieval(self, query_vector, topk=10, **kwargs):
        try:
            query_vector = np.array(query_vector)
            if len(query_vector.shape) == 1:
                query_vector = query_vector.reshape(1, -1)
            return self.batch_vector_search(
                self.chunk_label, "content", query_vector, topk=topk, **kwargs
            )[0]
        except:
            import traceback

            print("Failed to run DPR chunk retrieval return [], detail info:")
            traceback.print_exc()
            return []

    def get_cached_tensor(self, label_nodes, label, vector_field_name, device):
        emb_cache_key = f"{label}-{vector_field_name}"

        if emb_cache_key in self._emb_cache:
            filtered_nodes, filtered_vectors = self._emb_cache[emb_cache_key]
        else:
            try:
                vectors = label_nodes.get_attribute_values(vector_field_name)
            except Exception as e:
                logger.error(
                    f"get_cached_tensor index:{vector_field_name} not found in {label} with:{e}"
                )
                return [], []
            filtered_nodes = []
            filtered_vectors = []
            for node, vector in zip(label_nodes, vectors):
                if vector:
                    filtered_nodes.append(node)
                    filtered_vectors.append(vector)

            filtered_vectors = torch.tensor(filtered_vectors, dtype=torch.float32).to(
                device
            )
            with self._dict_lock:
                self._emb_cache[emb_cache_key] = [filtered_nodes, filtered_vectors]
        return filtered_nodes, filtered_vectors

    def vector_search(self, label, property_key, query_vector: list, topk=10, **kwargs):
        """
        Execute vector searching.

        :param label: entity label
        :param property_key: property key to search
        :param query_vector: the query vector (a list of float)
        :param topk: number of entities to return; default tot 10
        :param kwargs: other optional arguments
        """
        import torch

        if label == "Entity":
            nodes = self._backend_graph.vs
        else:
            try:
                nodes = self._backend_graph.vs.select(label=label)
            except (KeyError, ValueError):
                return []
        # print(f"len(nodes) = {len(nodes)}")
        vector_field_name = self._get_vector_field_name(property_key)
        device = configure_device()
        filtered_nodes, filtered_vectors = self.get_cached_tensor(
            label_nodes=nodes,
            label=label,
            vector_field_name=vector_field_name,
            device=device,
        )
        if len(filtered_nodes) == 0 or filtered_vectors.numel() == 0:
            return []

        if isinstance(query_vector, str):
            query_vector = self._vectorizer.vectorize(query_vector)
        query_vector = (
            torch.tensor(query_vector, dtype=torch.float32).unsqueeze(1).to(device)
        )
        cosine_similarity = filtered_vectors @ query_vector
        scores = 0.5 * cosine_similarity + 0.5

        top_data = scores.topk(k=min(topk, len(scores)), dim=0)
        top_indices = top_data.indices.to("cpu")
        top_values = top_data.values.to("cpu")
        items = []
        for index, score in zip(top_indices, top_values):
            node = nodes[index.item()]
            node_attributes = node.attributes()
            node_attributes["__labels__"] = [node_attributes["label"]]
            items.append({"node": node_attributes, "score": score.item()})
        return items

    def batch_vector_search(
        self, label, property_key, query_vector: list, topk=10, **kwargs
    ):
        """
        Execute vector searching.

        :param label: entity label
        :param property_key: property key to search
        :param query_vector: the query vector (a list of list[float])
        :param topk: number of entities to return; default tot 10
        :param kwargs: other optional arguments
        """
        try:

            def batch_cosine_similarity(v, M, require_norm=False):
                if require_norm:
                    v_norm = torch.norm(v, dim=1, keepdim=True)
                    M_norms = torch.norm(M, dim=1, keepdim=True)
                    dot_product = torch.matmul(M, v.T)
                    norm_product = torch.matmul(v_norm, M_norms.T)
                    return dot_product / norm_product.T

                else:
                    return torch.matmul(M, v.T)

            if label == "Entity":
                nodes = self._backend_graph.vs
            else:
                try:
                    nodes = self._backend_graph.vs.select(label=label)
                except (KeyError, ValueError):
                    return []

            vector_field_name = self._get_vector_field_name(property_key)
            device = configure_device()
            filtered_nodes, filtered_vectors = self.get_cached_tensor(
                label_nodes=nodes,
                label=label,
                vector_field_name=vector_field_name,
                device=device,
            )

            if len(filtered_nodes) == 0 or filtered_vectors.numel() == 0:
                return []
            query_vector = torch.tensor(query_vector, dtype=torch.float32).to(device)
            cosine_similarity = batch_cosine_similarity(query_vector, filtered_vectors)

            top_data = cosine_similarity.topk(
                k=min(topk, len(cosine_similarity)), dim=0
            )
            top_indices = top_data.indices.to("cpu")
            top_values = top_data.values.to("cpu")
            output = []
            for idx in range(query_vector.shape[0]):
                items = []
                for index, score in zip(top_indices[:, idx], top_values[:, idx]):
                    node = filtered_nodes[index.item()]
                    node_attributes = node.attributes()
                    if "__labels__" not in node_attributes:
                        node_attributes["__labels__"] = list(
                            set([node_attributes.get("label"), "Entity"])
                        )
                    items.append({"node": node_attributes, "score": score.item()})
                output.append(items)
            return output
        except Exception as e:
            logger.warning(f"batch_vector_search failed {e}", exc_info=True)
            return []

    @staticmethod
    def _get_vector_field_name(property_key: str) -> str:
        name = f"{property_key}_vector"
        name = MemoryGraph._to_snake_case(name)
        return "_" + name

    @staticmethod
    def _to_snake_case(name: str) -> str:
        words = re.findall("[A-Za-z][a-z0-9]*", name)
        result = "_".join(words).lower()
        return result

    def text_search(self, label, property_key, query_string: str, topk=10, **kwargs):
        """
        Execute vector searching.

        :param label: entity label
        :param property_key: property key
        :param query_string: query text
        :param topk: number of entities to return; default tot 10
        :param kwargs: other optional arguments
        """
        return []

    def upsert_subgraph(self, subgraph: Dict):
        """
        Upsert the subgraph with the memory graph.

        The subgraph is a dictionary create by `kag.builder.model.sub_graph.SubGraph.to_dict()`.

        :param subgraph: subgraph to upsert
        """

        def update_vertex_attributes(v, n):
            v.update_attributes(
                n["properties"], id=n["id"], name=n["name"], label=n["label"]
            )

        def update_edge_attributes(e, a):
            e.update_attributes(
                a["properties"],
                id=a["id"],
                label=a["label"],
                from_id=a["from"],
                from_type=a["fromType"],
                to_id=a["to"],
                to_type=a["toType"],
            )

        fresh_nodes = []
        for node in subgraph["resultNodes"]:
            try:
                vertex = self._backend_graph.vs.find(id=node["id"])
            except (KeyError, ValueError):
                fresh_nodes.append(node)
                continue
            update_vertex_attributes(vertex, node)
        old_num_vertices = len(self._backend_graph.vs)
        self._backend_graph.add_vertices(len(fresh_nodes))
        for k, node in enumerate(fresh_nodes):
            vertex = self._backend_graph.vs[old_num_vertices + k]
            update_vertex_attributes(vertex, node)

        fresh_arcs = []
        for arc in subgraph["resultEdges"]:
            try:
                edge = self._backend_graph.es.find(id=arc["id"])
            except (KeyError, ValueError):
                fresh_arcs.append(arc)
                continue
            update_edge_attributes(edge, arc)
        old_num_edges = len(self._backend_graph.es)
        fresh_edges = []
        filtered_arcs = []
        for arc in fresh_arcs:
            try:
                source = self._backend_graph.vs.find(id=arc["from"])
                target = self._backend_graph.vs.find(id=arc["to"])
                fresh_edges.append((source, target))
                filtered_arcs.append(arc)
            except:
                print(f"incorrect edge {arc}")
                continue
        self._backend_graph.add_edges(fresh_edges)
        for k, arc in enumerate(filtered_arcs):
            edge = self._backend_graph.es[old_num_edges + k]
            update_edge_attributes(edge, arc)

    def dump(self, dump_path=None):
        if dump_path:
            graph_pickle = os.path.join(dump_path, "graph")
        else:
            graph_pickle = os.path.join(self.ckpt_dir, "graph")
        self._backend_graph.write(graph_pickle, "picklez")
