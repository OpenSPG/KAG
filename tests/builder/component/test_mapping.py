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

import unittest
from kag.builder.model.sub_graph import SubGraph
from kag.builder.component.mapping.spo_mapping import SPOMapping


class TestSPOMapping(unittest.TestCase):
    def setUp(self):
        self.mapping_1 = SPOMapping()
        self.mapping_1.add_field_mappings(
            s_id_col="subject_id",
            p_type_col="predicate",
            o_id_col="object_id",
            s_type_col="subject_type",
            o_type_col="object_type",
        )
        self.mapping_1.add_sub_property_mapping(source_name="sub_property")
        self.mapping_2 = SPOMapping()
        self.mapping_2.add_field_mappings(
            s_id_col="subject_id",
            p_type_col="predicate",
            o_id_col="object_id",
            s_type_col="subject_type",
            o_type_col="object_type",
        )
        self.mapping_2.add_sub_property_mapping(
            source_name="sub_property_1", target_name="target_1"
        )
        self.mapping_2.add_sub_property_mapping(
            source_name="sub_property_2", target_name="target_2"
        )

    def test_invoke_with_dict_properties(self):
        # 准备一些模拟的数据
        input_data = {
            "subject_id": "s1",
            "predicate": "P1",
            "object_id": "o1",
            "subject_type": "Person",
            "object_type": "Organization",
            "sub_property": '{"target": "value"}',
        }

        # 调用invoke方法
        outputs = self.mapping_1.invoke(input_data)

        # 验证结果
        self.assertIsInstance(outputs, list)
        self.assertEqual(len(outputs), 1)
        sub_graph = outputs[0]
        self.assertIsInstance(sub_graph, SubGraph)
        self.assertEqual(len(sub_graph.nodes), 2)
        self.assertEqual(len(sub_graph.edges), 1)

        # 验证节点和边的详细信息
        s_node, o_node = sub_graph.nodes
        self.assertEqual(s_node.id, "s1")
        self.assertEqual(s_node.name, "s1")
        self.assertEqual(s_node.label, "Person")

        self.assertEqual(o_node.id, "o1")
        self.assertEqual(o_node.name, "o1")
        self.assertEqual(o_node.label, "Organization")

        edge = sub_graph.edges[0]
        self.assertEqual(edge.from_id, "s1")
        self.assertEqual(edge.from_type, "Person")
        self.assertEqual(edge.label, "P1")
        self.assertEqual(edge.to_id, "o1")
        self.assertEqual(edge.to_type, "Organization")
        self.assertEqual(edge.properties, {"target": "value"})

    def test_invoke_with_properties(self):
        # 准备一些模拟的数据
        input_data = {
            "subject_id": "s1",
            "predicate": "P1",
            "object_id": "o1",
            "subject_type": "Person",
            "object_type": "Organization",
            "sub_property_1": "value_1",
            "sub_property_2": "value_2",
        }

        # 调用invoke方法
        outputs = self.mapping_2.invoke(input_data)

        # 验证结果
        self.assertIsInstance(outputs, list)
        self.assertEqual(len(outputs), 1)
        sub_graph = outputs[0]
        self.assertIsInstance(sub_graph, SubGraph)
        self.assertEqual(len(sub_graph.nodes), 2)
        self.assertEqual(len(sub_graph.edges), 1)

        # 验证节点和边的详细信息
        s_node, o_node = sub_graph.nodes
        self.assertEqual(s_node.id, "s1")
        self.assertEqual(s_node.name, "s1")
        self.assertEqual(s_node.label, "Person")

        self.assertEqual(o_node.id, "o1")
        self.assertEqual(o_node.name, "o1")
        self.assertEqual(o_node.label, "Organization")

        edge = sub_graph.edges[0]
        self.assertEqual(edge.from_id, "s1")
        self.assertEqual(edge.from_type, "Person")
        self.assertEqual(edge.label, "P1")
        self.assertEqual(edge.to_id, "o1")
        self.assertEqual(edge.to_type, "Organization")
        self.assertEqual(
            edge.properties, {"target_1": "value_1", "target_2": "value_2"}
        )

    def test_add_sub_property_mapping_raises_value_error(self):
        # 尝试在已经设置了sub_property_col后再次添加映射
        self.mapping_1.sub_property_col = "sub_property"
        with self.assertRaises(ValueError):
            self.mapping_1.add_sub_property_mapping(source_name="another_property")


if __name__ == "__main__":
    unittest.main()
