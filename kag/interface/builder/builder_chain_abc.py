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
from typing import List, Any, Union

from concurrent.futures import ThreadPoolExecutor, as_completed
from kag.common.registry import Registrable
from kag.common.utils import flatten_2d_list, get_batch_boundaries
from knext.builder.builder_chain_abc import BuilderChainABC


class KAGBuilderChain(BuilderChainABC, Registrable):
    """
    KAGBuilderChain is a class that extends the BuilderChainABC and Registrable base classes.
    It is responsible for constructing and executing a workflow represented by a directed acyclic graph (DAG).
    Each node within the DAG is an instance of BuilderComponent, and the input for each node is processed in parallel.
    """

    def invoke(self, inputs: Union[Any, List], max_workers=10, **kwargs):
        """
        Invokes the builder chain to process the input data.

        Args:
            input: The input data to be processed.
            max_workers (int, optional): The maximum number of threads to use. Defaults to 10.
            **kwargs: Additional keyword arguments.

        Returns:
            List: The final output from the builder chain.
        """

        def execute_node(node, inputs: List[str]):
            """
            Executes a single node in the builder chain using parallel processing.

            Args:
                node: The node to be executed.
                inputs (List[str]): The list of input data for the node.

            Returns:
                List: The output from the node.
            """
            node_name = type(node).__name__.split(".")[-1]
            with ThreadPoolExecutor(max_workers) as inner_executor:
                inner_futures = [
                    inner_executor.submit(node.invoke, inp) for inp in inputs
                ]
                result = []
                from tqdm import tqdm

                for inner_future in tqdm(
                    as_completed(inner_futures),
                    total=len(inner_futures),
                    desc=f"[{node_name}]",
                    position=1,
                    leave=False,
                ):
                    # for inner_future in as_completed(inner_futures):
                    ret = inner_future.result()
                    result.extend(ret)
                return result

        chain = self.build(**kwargs)
        dag = chain.dag
        import networkx as nx

        if not isinstance(inputs, list):
            inputs = [inputs]
        nodes = list(nx.topological_sort(dag))
        node_outputs = {}
        # processed_node_names = []
        for node in nodes:
            # node_name = type(node).__name__.split(".")[-1]
            # processed_node_names.append(node_name)
            predecessors = list(dag.predecessors(node))
            if len(predecessors) == 0:
                node_input = inputs
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

    async def ainvoke(
        self, inputs: Union[Any, List[Any]], max_concurrency: int = 100, **kwargs
    ):
        """
        Invokes the builder chain to asynchronously process a batch of input data.
        Args:
            inputs: The input data to be processed.
            **kwargs: Additional keyword arguments.

        Returns:
            List: The final output from the builder chain.
        """

        async def execute_node(node, input_data: List):
            """
            Executes a single node in the builder chain asynchronously.

            Args:
                node: The node to be executed.
                input_data (List): The list of input data for the node.

            Returns:
                List: The output from the node.
            """

            async def ainvoke_with_semaphore(node, items, semaphore):
                async with semaphore:
                    return await node.ainvoke(items)

            batch_size = node.batch_size
            batchs = get_batch_boundaries(len(input_data), batch_size)
            tasks = []
            # The default implementation of `node.ainvoke` will process each data in the batch concurrently.
            # Therefore, the batch level concurrency is set to `max_concurrency // node.batch_size + 1`.
            semaphore = asyncio.Semaphore(max_concurrency // node.batch_size + 1)
            for batch in batchs:
                start, end = batch
                task = asyncio.create_task(
                    ainvoke_with_semaphore(node, input_data[start:end], semaphore)
                )
                print(
                    f"{node} task info: batch_size: {batch_size}, semaphore: {semaphore}, data range: {(start, end)}"
                )
                tasks.append(task)
            results = await asyncio.gather(*tasks)
            return flatten_2d_list(results)

        if not isinstance(inputs, List):
            inputs = [inputs]

        chain = self.build(**kwargs)
        dag = chain.dag
        import networkx as nx

        # sort nodes in the chain
        node_generations = list(nx.topological_generations(dag))
        nodes = flatten_2d_list(node_generations)
        node_outputs = {}
        for parallel_nodes in node_generations:
            tasks = []
            for node in parallel_nodes:
                predecessors = list(dag.predecessors(node))
                # collect node inputs from the predecessors
                if len(predecessors) == 0:
                    node_input = inputs
                    task = asyncio.create_task(execute_node(node, node_input))
                else:
                    node_input = []
                    for p in predecessors:
                        node_input.extend(flatten_2d_list(node_outputs[p]))
                    task = asyncio.create_task(execute_node(node, node_input))
                tasks.append(task)
            outputs = await asyncio.gather(*tasks)
            for node, node_output in zip(parallel_nodes, outputs):
                node_outputs[node] = node_output

        output_nodes = [node for node in nodes if dag.out_degree(node) == 0]
        final_output = []
        for node in output_nodes:
            if node in node_outputs:
                final_output.extend(node_outputs[node])

        return final_output
