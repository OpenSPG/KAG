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
from kag.common.registry import Registrable

from knext.builder.builder_chain_abc import BuilderChainABC


class KAGBuilderChain(BuilderChainABC, Registrable):
    def invoke(self, file_path, **kwargs):
        def execute_node(node, inputs: List[str]):
            result = []
            for item in inputs:
                res = node.invoke(item)
                result.extend(res)
            return result

        chain = self.build(file_path=file_path, **kwargs)
        dag = chain.dag
        import networkx as nx

        nodes = list(nx.topological_sort(dag))
        node_outputs = {}
        processed_node_names = []
        for node in nodes:
            node_name = type(node).__name__.split(".")[-1]
            processed_node_names.append(node_name)
            predecessors = list(dag.predecessors(node))
            if len(predecessors) == 0:
                node_input = [file_path]
                node_output = execute_node(node, node_input)
            else:
                node_input = []
                for p in predecessors:
                    node_input.extend(node_outputs[p])
                node_output = execute_node(node, node_input)
            node_outputs[node] = node_output
        output_nodes = [node for node in nodes if dag.out_degree(node) == 0]
        final_output = []
        for node in output_nodes:
            if node in node_outputs:
                final_output.extend(node_outputs[node])

        return final_output
