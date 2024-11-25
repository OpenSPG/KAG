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

import json
import tqdm
from typing import Dict, List, Type

from kag.builder.component.base import Aligner
from kag.builder.model.sub_graph import SubGraph
from kag.common.base.runnable import Input, Output

from kag.common.semantic_infer import SemanticEnhance


def load_data(data_file):
    raw_dicts = [json.loads(line.strip()) for line in open(data_file, "r").readlines()]
    ret_data = {}
    for ix, data in enumerate(raw_dicts):
        key = ""
        for node in data["resultNodes"]:
          if node["label"] == 'Chunk':
              content = node["properties"]["content"]
              key = content
        if key in ret_data:
            raise ValueError(f"duplicate key: {key}")
        ret_data[key] = data
    return ret_data


def count_expanded_concepts(data):
    nums = {}
    for key, data in data.items():
        num_concept = 0
        for node in data["resultNodes"]:
            if node["label"] == 'SemanticConcept':
                num_concept += 1
        nums[key] = num_concept
    return nums


class SemanticAligner(Aligner, SemanticEnhance):
    """
    A class for semantic alignment and enhancement, inheriting from Aligner and SemanticEnhance.
    """

    def __init__(self, **kwargs):
        Aligner.__init__(self, **kwargs)
        SemanticEnhance.__init__(self, **kwargs)
        self.prg_bar = tqdm.tqdm(desc="Semantic Alignment")

        # RESUME_FROM = os.getenv("KAG_INDEXER_CONCEPT_EXPAND_RESUME_FROM", None)
        # self.resumed_data = load_data(RESUME_FROM) if RESUME_FROM else {}
        # save_as = os.getenv("KAG_INDEXER_CORPUS_PATH", '').split('/')[-1].replace(".jsonl", "_align.jsonl")
        # self.write_file = open(save_as, "w")
        self.resumed_data = {}

    @property
    def input_types(self) -> Type[Input]:
        return SubGraph

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    @staticmethod
    def _dedup_dict_list(sequence: List[Dict], keys: List[str]) -> List[Dict]:
        new_seq = []
        key_map = set()
        for ele in sequence:
            key = '-'.join([str(ele.get(k)) for k in keys])
            if key not in key_map:
                key_map.add(key)
                new_seq.append(ele)
        return new_seq

    def invoke(self, input: SubGraph, **kwargs) -> List[SubGraph]:
        """
        Generates and adds concept nodes based on extracted entities and their context.

        Args:
            input (SubGraph): The input subgraph.
            **kwargs: Additional keyword arguments.

        Returns:
            List[SubGraph]: A list containing the updated subgraph.
        """
        expanded_concept_nodes = []
        expanded_concept_edges = []

        context = [
            node.properties.get("content")
            for node in input.nodes if node.label == 'Chunk'
        ]
        context = context[0] if context else None
        
        num_concept = len([1 for node in self.resumed_data.get(context, {}).get("resultNodes", []) if node['label'] == 'SemanticConcept'])

        if (context in self.resumed_data) and num_concept > 0:
            input = SubGraph.from_dict(self.resumed_data[context])
        else:
            # print("re-processing case")
            for node in input.nodes:
                if node.id == "" or node.name == "" or node.label == 'Chunk':
                    continue
                expand_dict = self.expand_semantic_concept(node.name, context=context, target=None)
                expand_nodes = [
                    {
                        "id": info["name"], "name": info["name"],
                        "label": self.concept_label,
                        # "properties": {"desc": info["desc"]}
                        "properties": {}
                    }
                    for info in expand_dict
                    if info["name"] != node.name
                ]
                expanded_concept_nodes.extend(expand_nodes)
                path_nodes = [node.to_dict()] + expand_nodes
                for ix, concept in enumerate(path_nodes):
                    if ix == 0:
                        continue
                    expanded_concept_edges.append({
                        "s_id": path_nodes[ix-1]["id"],
                        "s_label": path_nodes[ix-1]["label"],
                        "p": self.hyper_edge,
                        "o_id": path_nodes[ix]["id"],
                        "o_label": path_nodes[ix]["label"]
                    })

            expanded_concept_nodes = self._dedup_dict_list(expanded_concept_nodes, ['id', 'label'])
            expanded_concept_edges = self._dedup_dict_list(expanded_concept_edges, ['s_id', 'o_id'])

            [input.add_node(**n) for n in expanded_concept_nodes]
            [input.add_edge(**e) for e in expanded_concept_edges]

        # self.write_file.write(json.dumps(input.to_dict(), ensure_ascii=False)+"\n")
        self.prg_bar.update(1)

        return [input]
