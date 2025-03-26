import networkx as nx
import concurrent.futures

from typing import Dict, List, Tuple
import time

import logging

from kag.common.conf import KAG_CONFIG
from kag.interface.solver.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import RetrievedData, KgGraph
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponent,
)


logger = logging.getLogger()


def _merge_graph(input_data: List[RetrievedData]):
    graph_data = None
    other_datas = []
    if input_data is not None:
        for data in input_data:
            if not isinstance(data, KgGraph):
                other_datas.append(data)
                continue
            if graph_data is None:
                graph_data = data
                continue
            graph_data.merge_kg_graph(data)
        graph_datas = [data for data in input_data if isinstance(data, KgGraph)]
        graph_data = graph_datas[0] if len(graph_datas) > 0 else None
    return graph_data, other_datas


class KAGFlow:
    def __init__(self, flow_id, nl_query, lf_nodes: List[LogicNode], flow_str):
        # Initialize the KAGFlow with natural language query, logic nodes, and flow string
        self.nl_query = nl_query
        self.lf_nodes: List[LogicNode] = lf_nodes
        self.flow_str = flow_str.strip()
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, FlowComponent] = {}
        self.parse_flow()
        self.graph_data = None
        self.flow_id = flow_id

    def _add_node(self, node_name: str):
        # Add a node to the graph if it doesn't already exist
        if node_name not in self.nodes:
            if node_name not in KAG_CONFIG.all_config.keys():
                raise ValueError(f"Unknown node type: {node_name}")
            self.nodes[node_name] = FlowComponent.from_config(
                KAG_CONFIG.all_config[node_name]
            )

    def _add_edge(self, src: str, dst: str):
        # Add an edge between two nodes, ensuring both nodes exist in the graph
        self._add_node(src)
        self._add_node(dst)
        self.graph.add_edge(src, dst)

    def parse_flow(self):
        logger.info(f"{self.nl_query} Parsing flow string: {self.flow_str}")
        paths = self.flow_str.split(";")

        for path in paths:
            path = path.strip()
            logger.info(f"{self.nl_query} Processing path: {path}")

            if "->" in path:
                parts = path.split("->")
                for current_part, next_part in zip(parts, parts[1:]):
                    current_nodes = [n.strip() for n in current_part.split(",")]
                    next_nodes = [n.strip() for n in next_part.split(",")]
                    logger.info(
                        f"{self.nl_query} Adding edges from {current_nodes} to {next_nodes}"
                    )

                    for src in current_nodes:
                        for dst in next_nodes:
                            self._add_edge(src, dst)
            else:
                self._add_node(path.strip())
                logger.info(f"{self.nl_query} Added node: {path.strip()}")

    def execute_node(self, node_name: str, **kwargs) -> List[RetrievedData]:
        logger.info(f"{self.nl_query} Executing node: {node_name}")
        start_time = time.time()

        input_data = []
        predecessors = self.graph.predecessors(node_name)
        for pre_node in predecessors:
            if pre_node not in self.nodes:
                raise ValueError(f"{self.nl_query} Unknown node name: {type(pre_node)}")
            if not self.nodes[pre_node].result:
                continue
            if self.nodes[pre_node].is_break():
                # stop this graph
                self.nodes[node_name].result = self.nodes[pre_node].result
                self.nodes[node_name].break_flag = True
                logger.info(
                    f"{self.nl_query} Node {node_name} stopped due to break flag in {pre_node}"
                )
                return self.nodes[node_name].result
            if isinstance(self.nodes[pre_node].result, list):
                input_data.extend(self.nodes[pre_node].result)
            else:
                input_data.append(self.nodes[pre_node].result)
        # Execute a specific node in the graph and return the results
        if input_data is None:
            input_data = []
        self.graph_data, _ = _merge_graph(input_data)
        cur_graph_data = KgGraph()
        if self.graph_data:
            cur_graph_data.merge_kg_graph(self.graph_data)
        node = self.nodes[node_name]
        if isinstance(node, FlowComponent):
            res = node.invoke(
                query=self.nl_query,
                logic_nodes=self.lf_nodes,
                graph_data=cur_graph_data,
                datas=input_data,
                flow_id=self.flow_id,
                **kwargs,
            )
            node.break_judge(
                query=self.nl_query,
                logic_nodes=self.lf_nodes,
                graph_data=cur_graph_data,
                datas=input_data,
                flow_id=self.flow_id,
            )
            logger.info(
                f"{self.nl_query} Node {node_name} executed in {time.time() - start_time:.2f} seconds"
            )
            return res
        else:
            raise ValueError(f"{self.nl_query} Unknown node type: {type(node)}")

    def execute(self, **kwargs) -> Tuple[KgGraph, List[RetrievedData]]:
        logger.info(f"{self.nl_query} Starting KAGFlow execution")
        start_time = time.time()

        """
        Execute the DAG workflow and collect results from all nodes.

        Returns:
            List[RetrievedData]: Aggregated results from all sink nodes.

        Raises:
            ValueError: If the graph contains cycles or is not a valid DAG.
            RuntimeError: If no executable nodes are found during execution or if a node execution fails.
        """
        try:
            # Validate the graph structure and retrieve topological order
            if not nx.is_directed_acyclic_graph(self.graph):
                cycles = list(nx.simple_cycles(self.graph))
                raise ValueError(f"{self.nl_query} Graph contains cycles: {cycles[0]}")
            topological_order = list(nx.topological_sort(self.graph))
            logger.info(
                f"{self.nl_query} Topological order retrieved: {topological_order}"
            )
        except nx.NetworkXUnfeasible:
            raise ValueError(
                f"{self.nl_query} Graph is not a valid Directed Acyclic Graph (DAG)"
            )

        with concurrent.futures.ThreadPoolExecutor() as executor:
            remaining_nodes = list(topological_order)
            while remaining_nodes:
                # Identify executable nodes (all predecessors already executed)
                current_level = [
                    node
                    for node in remaining_nodes
                    if all(
                        pred not in remaining_nodes
                        for pred in self.graph.predecessors(node)
                    )
                ]
                if not current_level:
                    raise RuntimeError(
                        f"{self.nl_query} Execution stuck - no executable nodes found. Check dependencies."
                    )
                logger.info(
                    f"{self.nl_query} Current level nodes to execute: {current_level}"
                )

                # Execute current level nodes in parallel
                futures = {
                    executor.submit(self.execute_node, node, **kwargs): node
                    for node in current_level
                }

                for future in concurrent.futures.as_completed(futures):
                    node = futures[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        raise RuntimeError(
                            f"{self.nl_query} Node '{node}' execution failed: {str(e)}"
                        )

                    # Update results and remove node from remaining nodes
                    self.nodes[node].result = result
                    remaining_nodes.remove(node)
                    logger.info(f"{self.nl_query} Node {node} executed successfully")

        # Collect results from sink nodes (nodes with no outgoing edges)
        sink_nodes: List[str] = [
            node for node in self.graph.nodes() if self.graph.out_degree(node) == 0
        ]
        results = []
        for node_name in sink_nodes:
            node = self.nodes[node_name]
            if not node.result:
                continue
            if isinstance(node.result, list):
                results.extend(node.result)
            else:
                results.append(node.result)
        graph_data, others = _merge_graph(results)
        if graph_data is not None:
            self.graph_data = graph_data
        logger.info(
            f"{self.nl_query} KAGFlow execution completed in {time.time() - start_time:.2f} seconds"
        )
        return self.graph_data, others
