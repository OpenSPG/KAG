import networkx as nx
import concurrent.futures

from typing import Dict, List, Tuple

from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_component.flow_component import \
    FlowComponent
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_types.logic_node.logic_node import \
    LogicNode
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_types.retrieved_data import RetrievedData, \
    GraphData


def _merge_graph(input_data: List[RetrievedData]):
    graph_data = None
    other_datas = []
    if input_data is not None:
        for data in input_data:
            if not isinstance(data, GraphData):
                other_datas.append(data)
            if graph_data is None:
                graph_data = data
                continue
            graph_data.merge_graph(data)
        graph_datas = [data for data in input_data if isinstance(data, GraphData)]
        graph_data = graph_datas[0] if len(graph_datas) > 0 else None
    return graph_data, other_datas


class KAGFlow:
    def __init__(self, nl_query, lf_nodes: List[LogicNode], flow_str):
        # Initialize the KAGFlow with natural language query, logic nodes, and flow string
        self.nl_query = nl_query
        self.lf_nodes: List[LogicNode] = lf_nodes
        self.flow_str = flow_str.strip(' ', '')
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, FlowComponent] = {}
        self.parse_flow()

    def _add_node(self, node_name: str):
        # Add a node to the graph if it doesn't already exist
        if node_name not in self.nodes:
            self.nodes[node_name] = FlowComponent(name=node_name)

    def _add_edge(self, src: str, dst: str):
        # Add an edge between two nodes, ensuring both nodes exist in the graph
        self._add_node(src)
        self._add_node(dst)
        self.graph.add_edge(src, dst)

    def parse_flow(self):
        # Parse the flow string to build the graph structure
        paths = self.flow_str.split(';')

        for path in paths:
            path = path.strip()

            if '->' in path:
                parts = path.split('->')
                for current_part, next_part in zip(parts, parts[1:]):
                    current_nodes = [n.strip() for n in current_part.split(',')]
                    next_nodes = [n.strip() for n in next_part.split(',')]

                    for src in current_nodes:
                        for dst in next_nodes:
                            self._add_edge(src, dst)
            else:
                self._add_node(path.strip())

    def execute_node(self, node_name: str, input_data: List[RetrievedData] = None) -> List[RetrievedData]:
        # Execute a specific node in the graph and return the results
        if input_data is None:
            input_data = []
        graph_data, _ = _merge_graph(input_data)
        node = self.nodes[node_name]
        if isinstance(node, FlowComponent):
            return node.invoke(query=self.nl_query, logic_nodes=self.lf_nodes, graph_data=graph_data, datas=input_data)
        else:
            raise ValueError(f"Unknown node type: {type(node)}")

    def execute(self) -> Tuple[GraphData, List[RetrievedData]]:
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
                raise ValueError(f"Graph contains cycles: {cycles[0]}")
            topological_order = list(nx.topological_sort(self.graph))
        except nx.NetworkXUnfeasible:
            raise ValueError("Graph is not a valid Directed Acyclic Graph (DAG)")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            remaining_nodes = list(topological_order)
            while remaining_nodes:
                # Identify executable nodes (all predecessors already executed)
                current_level = [
                    node
                    for node in remaining_nodes
                    if all(pred not in remaining_nodes
                           for pred in self.graph.predecessors(node))
                ]
                if not current_level:
                    raise RuntimeError("Execution stuck - no executable nodes found. Check dependencies.")

                # Execute current level nodes in parallel
                futures = {executor.submit(self.execute_node, node): node for node in current_level}

                for future in concurrent.futures.as_completed(futures):
                    node = futures[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        raise RuntimeError(f"Node '{node}' execution failed: {str(e)}")

                    # Update results and remove node from remaining nodes
                    self.nodes[node].result = result
                    remaining_nodes.remove(node)

        # Collect results from sink nodes (nodes with no outgoing edges)
        sink_nodes: List[str] = [node for node in self.graph.nodes() if self.graph.out_degree(node) == 0]
        results = []
        for node_name in sink_nodes:
            node = self.nodes[node_name]
            if node.result:
                results.extend(node.result)
        graph_data, others = _merge_graph(results)
        return graph_data, others
