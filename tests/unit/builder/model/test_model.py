# -*- coding: utf-8 -*-
from kag.builder.model.sub_graph import Node, Edge, SubGraph


def test_node():
    node = Node("1", "node", "Concept", {"desc": "a graph node"})
    node_dict = node.to_dict()
    new_node = Node.from_dict(node_dict)
    assert node.id == new_node.id
    assert node == new_node


def test_edge():
    node1 = Node("1", "node1", "Concept", {"desc": "a graph node"})
    node2 = Node("2", "node2", "Concept", {"desc": "another graph node"})
    edge = Edge("1", node1, node2, "link", {"desc": "node1 links to node2"})
    edge_dict = edge.to_dict()
    new_edge = Edge.from_dict(edge_dict)
    assert edge.from_id == new_edge.from_id
    assert edge.from_type == new_edge.from_type
    assert edge.to_id == new_edge.to_id
    assert edge.to_type == new_edge.to_type
    assert edge.label == new_edge.label
    assert edge.properties == new_edge.properties


def test_subgraph():
    node1 = Node("1", "node1", "Concept", {"desc": "a graph node"})
    node2 = Node("2", "node2", "Concept", {"desc": "another graph node"})
    edge = Edge("1", node1, node2, "link", {"desc": "node1 links to node2"})
    subgraph = SubGraph(nodes=[node1, node2], edges=[edge])
    subgraph.add_node("3", "node3", "Concept", {"desc": "3th graph node"})
    subgraph.add_edge(
        "1", "Concept", "link", "3", "Concept", {"desc": "node1 links to node3"}
    )

    subgraph_dict = subgraph.to_dict()
    new_subgraph = SubGraph.from_dict(subgraph_dict)
    assert len(subgraph.nodes) == len(new_subgraph.nodes)
    assert len(subgraph.edges) == len(new_subgraph.edges)
    node_ids = set([x.id for x in subgraph.nodes])
    new_node_ids = set([x.id for x in new_subgraph.nodes])
    assert node_ids == new_node_ids
