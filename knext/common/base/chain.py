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

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Union, Type, List, Dict

import networkx as nx
from tqdm import tqdm

from knext.common.base.runnable import Runnable
from knext.common.base.restable import RESTable


class Chain(Runnable, RESTable):
    """
    Base class for creating structured sequences of calls to components.
    """

    """The execution process of Chain, represented by a dag structure."""
    dag: nx.DiGraph

    def invoke(self, input: str, max_workers, **kwargs):
        node_results = {}
        futures = []

        def execute_node(node, inputs: List[str]):
            with ThreadPoolExecutor(max_workers) as inner_executor:
                inner_futures = [
                    inner_executor.submit(node.invoke, inp) for inp in inputs
                ]
                result = []
                for idx, inner_future in tqdm(
                    enumerate(as_completed(inner_futures)),
                    total=len(inner_futures),
                    desc=f"Processing {node.name}",
                ):
                    ret = inner_future.result()
                    result.extend(ret)
                return node, result

        # Initialize a ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers) as executor:
            # Find the starting nodes (nodes with no predecessors)
            start_nodes = [
                node for node in self.dag.nodes if self.dag.in_degree(node) == 0
            ]

            # Initialize the first set of tasks
            for node in start_nodes:
                futures.append(executor.submit(execute_node, node, [input]))

            # Process nodes as futures complete
            while futures:
                for future in as_completed(futures):
                    node, result = future.result()
                    node_results[node] = result
                    futures.remove(future)

                    # Submit successors for execution
                    successors = list(self.dag.successors(node))
                    for successor in successors:
                        # Check if all predecessors of the successor have finished processing
                        if all(
                            pred in node_results
                            for pred in self.dag.predecessors(successor)
                        ):
                            # Gather all inputs from predecessors for this successor
                            inputs = []
                            for pred in self.dag.predecessors(successor):
                                inputs.extend(node_results[pred])
                            futures.append(
                                executor.submit(execute_node, successor, inputs)
                            )

        # Collect the final results from the output nodes
        output_nodes = [
            node for node in self.dag.nodes if self.dag.out_degree(node) == 0
        ]
        final_output = []
        for node in output_nodes:
            if node in node_results:
                final_output.extend(node_results[node])

        return final_output

    def batch(self, inputs: List[str], max_workers, **kwargs):
        for i in inputs:
            self.invoke(i, max_workers, **kwargs)

    def to_rest(self):
        from knext.builder import rest

    def __rshift__(
        self,
        other: Union[
            Type["Chain"],
            List[Type["Chain"]],
            Type["Component"],
            List[Type["Component"]],
            None,
        ],
    ):
        """
        Implements the right shift operator ">>" functionality to link Component or Chain objects.

        This method can handle single Component/Chain objects or lists of them.
        When linking Components, a new DAG (Directed Acyclic Graph) is created to represent the data flow connection.
        When linking Chain objects, the DAGs of both Chains are merged.

        Parameters:
        other (Union[Type["Chain"], List[Type["Chain"]], Type["Component"], List[Type["Component"]], None]):
            The subsequent steps to link, which can be a single or list of Component/Chain objects.

        Returns:
        A new Chain object with a DAG that represents the linked data flow between the current Chain and the parameter other.
        """
        from knext.common.base.component import Component

        if not other:
            return self
        # If other is not a list, convert it to a list
        if not isinstance(other, list):
            other = [other]

        dag_list = []
        for o in other:
            if not o:
                dag_list.append(o.dag)
            # If o is a Component, create a new DAG and try to add o to the graph
            if isinstance(o, Component):
                end_nodes = [
                    node
                    for node, out_degree in self.dag.out_degree()
                    if out_degree == 0 or node._last
                ]
                dag = nx.DiGraph(self.dag)
                if len(end_nodes) > 0:
                    for end_node in end_nodes:
                        dag.add_edge(end_node, o)
                dag.add_node(o)
                dag_list.append(dag)
            # If o is a Chain, merge the DAGs of self and o
            elif isinstance(o, Chain):
                combined_dag = nx.compose(self.dag, o.dag)
                end_nodes = [
                    node
                    for node, out_degree in self.dag.out_degree()
                    if out_degree == 0 or node._last
                ]
                start_nodes = [
                    node for node, in_degree in o.dag.in_degree() if in_degree == 0
                ]

                if len(end_nodes) > 0 and len(start_nodes) > 0:
                    for end_node in end_nodes:
                        for start_node in start_nodes:
                            combined_dag.add_edge(end_node, start_node)
        # Merge all DAGs and create the final Chain object
        final_dag = nx.compose_all(dag_list)
        return Chain(dag=final_dag)
