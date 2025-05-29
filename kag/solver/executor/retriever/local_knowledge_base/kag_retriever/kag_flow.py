from kag.interface.common.llm_client import LLMClient
import networkx as nx
import concurrent.futures

from typing import Dict, List, Tuple
import time

import logging

from kag.common.conf import KAG_CONFIG
from kag.common.config import get_default_chat_llm_config
from kag.common.parser.logic_node_parser import GetSPONode
from kag.interface import Task
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.model.one_hop_graph import RetrievedData, KgGraph
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponent,
    FlowComponentTask,
)
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.kag_lf_cmponent import (
    KagLogicalFormComponent,
)

logger = logging.getLogger()


def _merge_graph(graph_data, input_data: List[RetrievedData]):
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
    return graph_data, other_datas


class KAGFlow:
    def __init__(self, flow_str, llm_client: LLMClient = None):
        # Initialize the KAGFlow with natural language query, logic nodes, and flow string
        self.flow_str = flow_str.strip()

        self.default_flow_component = {
            "kg_cs": {
                "type": "kg_cs_open_spg",
                "path_select": {"type": "exact_one_hop_select"},
                "entity_linking": {
                    "type": "entity_linking",
                    "recognition_threshold": 0.9,
                    "exclude_types": ["Chunk"],
                },
                "llm": llm_client.to_config() if llm_client else None,
            },
            "kg_fr": {
                "type": "kg_fr_open_spg",
                "top_k": 20,
                "path_select": {
                    "type": "fuzzy_one_hop_select",
                    "llm_client": llm_client.to_config(),
                },
                "ppr_chunk_retriever_tool": {
                    "type": "ppr_chunk_retriever",
                    "llm_client": llm_client.to_config(),
                },
                "entity_linking": {
                    "type": "entity_linking",
                    "recognition_threshold": 0.8,
                    "exclude_types": ["Chunk"],
                },
                "llm": llm_client.to_config(),
            },
            "rc": {
                "type": "rc_open_spg",
                "vector_chunk_retriever": {
                    "type": "vector_chunk_retriever",
                },
                "top_k": 20,
            },
            "kag_merger": {
                "type": "kg_merger",
                "top_k": 20,
                "llm_module": llm_client.to_config(),
                "summary_prompt": {"type": "default_thought_then_answer"},
            },
        }
        graph, nodes = self.parse_flow()
        self.graph = graph
        self.nodes = nodes

    def parse_flow(self):
        execute_graph = nx.DiGraph()
        component_nodes: Dict[str, FlowComponent] = {}

        def _add_node(node_name: str):
            # Add a node to the graph if it doesn't already exist
            if node_name not in component_nodes:
                if (
                    node_name not in KAG_CONFIG.all_config.keys()
                    and node_name not in self.default_flow_component.keys()
                ):
                    raise ValueError(f"Unknown node type: {node_name}")
                component_conf = KAG_CONFIG.all_config.get(
                    node_name, self.default_flow_component.get(node_name)
                )
                component_nodes[node_name] = FlowComponent.from_config(component_conf)
                execute_graph.add_node(node_name)

        def _add_edge(src: str, dst: str):
            # Add an edge between two nodes, ensuring both nodes exist in the graph
            _add_node(src)
            _add_node(dst)
            execute_graph.add_edge(src, dst)

        logger.info(f"Parsing flow string: {self.flow_str}")
        paths = self.flow_str.split(";")

        for path in paths:
            path = path.strip()
            logger.info(f"Processing path: {path}")

            if "->" in path:
                parts = path.split("->")
                for current_part, next_part in zip(parts, parts[1:]):
                    current_nodes = [n.strip() for n in current_part.split(",")]
                    next_nodes = [n.strip() for n in next_part.split(",")]
                    logger.info(f"Adding edges from {current_nodes} to {next_nodes}")

                    for src in current_nodes:
                        for dst in next_nodes:
                            _add_edge(src, dst)
            else:
                _add_node(path.strip())
                logger.info(f" Added node: {path.strip()}")
        return execute_graph, component_nodes

    def execute_node(
        self,
        query,
        flow_id,
        node_name: str,
        cur_task: FlowComponentTask,
        executor_task: Task,
        node_task_map,
        processed_logical_nodes: List[LogicNode],
        **kwargs,
    ) -> FlowComponentTask:
        logger.info(f"{query} Executing node: {node_name}")
        node = self.nodes[node_name]
        start_time = time.time()

        input_data = []
        predecessors = self.graph.predecessors(node_name)
        input_components = []
        for pre_node in predecessors:
            if pre_node not in node_task_map:
                raise ValueError(f"{query} Unknown node name: {type(pre_node)}")
            if not node_task_map[pre_node].result:
                continue
            input_components.append(node_task_map[pre_node])

            if node_task_map[pre_node].is_break() and isinstance(
                node, KagLogicalFormComponent
            ):
                # stop this graph
                node_task_map[node_name].result = node_task_map[pre_node].result
                node_task_map[node_name].break_flag = True
                logger.info(
                    f"{query} Node {node_name} stopped due to break flag in {pre_node}"
                )
                cur_task.result = node_task_map[node_name].result
                return cur_task
            if isinstance(node_task_map[pre_node].result, list):
                input_data.extend(node_task_map[pre_node].result)
            else:
                input_data.append(node_task_map[pre_node].result)
        # Execute a specific node in the graph and return the results
        if input_data is None:
            input_data = []

        cur_graph_data = kwargs.get("context_graph", KgGraph())
        cur_graph_data, _ = _merge_graph(cur_graph_data, input_data)
        cur_task.graph_data = cur_graph_data

        if isinstance(node, FlowComponent):
            res = node.invoke(
                cur_task=cur_task,
                executor_task=executor_task,
                processed_logical_nodes=processed_logical_nodes,
                input_components=input_components,
                flow_id=flow_id,
                **kwargs,
            )
            node.break_judge(
                cur_task=cur_task,
                flow_id=flow_id,
                **kwargs,
            )
            logger.info(
                f"{query} Node {node_name} executed in {time.time() - start_time:.2f} seconds"
            )
            cur_task.result = res
            return cur_task
        else:
            raise ValueError(f"{query} Unknown node type: {type(node)}")

    def execute(
        self, flow_id, nl_query, lf_nodes: List[GetSPONode], executor_task, **kwargs
    ) -> Tuple[KgGraph, List[RetrievedData]]:
        logger.info(f"{nl_query} Starting KAGFlow execution")
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
                raise ValueError(f"{nl_query} Graph contains cycles: {cycles[0]}")
            topological_order = list(nx.topological_sort(self.graph))
            logger.info(f"{nl_query} Topological order retrieved: {topological_order}")
        except nx.NetworkXUnfeasible:
            raise ValueError(
                f"{nl_query} Graph is not a valid Directed Acyclic Graph (DAG)"
            )
        processed_logical_nodes = []
        results = []
        for logical_node in lf_nodes:
            node_task_map = {}
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
                            f"{nl_query} Execution stuck - no executable nodes found. Check dependencies."
                        )
                    logger.info(
                        f"{nl_query} Current level nodes to execute: {current_level}"
                    )
                    cur_level_tasks = []
                    for node in current_level:
                        cur_task = FlowComponentTask()
                        cur_task.task_name = node
                        cur_task.logical_node = logical_node
                        cur_task.query = nl_query
                        cur_level_tasks.append(cur_task)
                        node_task_map[cur_task.task_name] = cur_task
                    # Execute current level nodes in parallel
                    futures = {
                        executor.submit(
                            self.execute_node,
                            flow_id=flow_id,
                            query=nl_query,
                            node_name=node.task_name,
                            cur_task=node,
                            executor_task=executor_task,
                            node_task_map=node_task_map,
                            processed_logical_nodes=processed_logical_nodes,
                            **kwargs,
                        ): node
                        for node in cur_level_tasks
                    }

                    for future in concurrent.futures.as_completed(futures):
                        node = futures[future]
                        try:
                            result = future.result()
                        except Exception as e:
                            raise RuntimeError(
                                f"{nl_query} Node '{node}' execution failed: {str(e)}"
                            )
                        node_task_map[result.task_name] = result
                        # Update results and remove node from remaining nodes
                        remaining_nodes.remove(node.task_name)
                        logger.info(f"Node {node.task_name} executed successfully")
            # Collect results from sink nodes (nodes with no outgoing edges)
            sink_nodes: List[str] = [
                node for node in self.graph.nodes() if self.graph.out_degree(node) == 0
            ]
            for node_name in sink_nodes:
                node = node_task_map[node_name]
                if not node.result:
                    continue
                if isinstance(node.result, list):
                    results.extend(node.result)
                else:
                    results.append(node.result)
            processed_logical_nodes.append(logical_node)
        graph_data = KgGraph()
        graph_data, others = _merge_graph(graph_data, results)
        logger.info(
            f"{nl_query} KAGFlow execution completed in {time.time() - start_time:.2f} seconds"
        )
        return graph_data, others
