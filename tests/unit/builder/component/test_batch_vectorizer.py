# -*- coding: utf-8 -*-
import asyncio
from kag.interface import VectorizerABC
from kag.builder.model.sub_graph import SubGraph


def xtest_batch_vectorizer():
    batch_vectorizer = VectorizerABC.from_config(
        {
            "type": "batch",
            "vectorize_model": {
                "type": "bge",
                "path": "~/.cache/vectorizer/BAAI/bge-base-zh-v1.5",
                "url": "",
                "vector_dimensions": 768,
            },
        }
    )
    names = [
        "精卫填海",
        "海阔天空",
        "空前绝后",
        "后来居上",
        "上下一心",
        "心旷神怡",
        "怡然自得",
        "得心应手",
    ]
    subgraph = SubGraph([], [])
    for name in names:
        subgraph.add_node(id=name, name=name, label="Chunk")

    new_graph = batch_vectorizer.invoke(subgraph)[0]
    assert len(subgraph.nodes) == len(new_graph.nodes)
    for node in new_graph.nodes:
        assert node.name in names
        assert "_name_vector" in node.properties
        assert len(node.properties["_name_vector"]) == 768


async def atest_batch_vectorizer():
    batch_vectorizer = VectorizerABC.from_config(
        {
            "type": "batch",
            "vectorize_model": {
                "type": "openai",
                "api_key": "",
                "base_url": "https://api.siliconflow.cn/v1/",
                "model": "BAAI/bge-m3",
                "vector_dimensions": 1024,
            },
        }
    )
    names = [
        "精卫填海",
        "海阔天空",
        "空前绝后",
        "后来居上",
        "上下一心",
        "心旷神怡",
        "怡然自得",
        "得心应手",
    ]
    subgraph = SubGraph([], [])
    for name in names:
        subgraph.add_node(id=name, name=name, label="Chunk")

    new_graph = await batch_vectorizer.ainvoke(subgraph)
    new_graph = new_graph[0]
    assert len(subgraph.nodes) == len(new_graph.nodes)
    for node in new_graph.nodes:
        assert node.name in names
        assert "_name_vector" in node.properties
        assert len(node.properties["_name_vector"]) == 1024
    return new_graph


def test_async_batch_vectorizer():
    asyncio.run(atest_batch_vectorizer())
