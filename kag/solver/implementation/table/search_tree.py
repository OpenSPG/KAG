from typing import List
import time
import json

import networkx as nx

from knext.reasoner.rest.models.ca_pipeline import CaPipeline
from knext.reasoner.rest.models.edge import Edge
from knext.reasoner.rest.models.node import Node
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool


class SearchTreeNode:
    """
    tree node
    """

    def __init__(self, question, func):
        self.question = question
        self.func = func
        self.time_stamp = int(time.time() * 1000)
        self.answer = None
        self.sub_graph = None
        self.answer_desc = None
        self.subgraph = None

    def __str__(self):
        return f"Node(question={self.question},answer={self.answer})"

    def _id(self):
        return f"Node(question={self.question},func={self.func})"

    def __hash__(self):
        return hash(self._id())

    def __eq__(self, other):
        if isinstance(other, SearchTreeNode):
            return self._id() == other._id()
        return False


class SearchTree:
    def __init__(self, root_question, dk=None):
        self.root_node = SearchTreeNode(root_question, "root")
        self.dag = nx.DiGraph()
        self.dag.add_node(self.root_node)
        self.now_processing_node = self.root_node
        self.now_plan = None
        self.faild_plan = []

        # 领域知识，Domain Knowledge
        self.dk = dk

        self.id_allocator = IDAllocator()

    def has_node(self, node: SearchTreeNode):
        return self.dag.has_node(node)

    def get_node_in_graph(self, node: SearchTreeNode):
        for n in self.dag.nodes():
            if n == node:
                return n
        return None

    def set_now_plan(self, now_plan):
        if self.now_plan is not None:
            self.faild_plan.append(self.now_plan)
        self.now_plan = now_plan
        self.now_processing_node = self.root_node

    def get_now_plan(self):
        return self.now_plan

    def add_now_procesing_ndoe(self, new_node):
        old_node = self.get_now_processing_node()
        if old_node == new_node:
            return
        self.dag.add_node(new_node)
        self.dag.add_edge(old_node, new_node)
        self.now_processing_node = new_node

    def get_now_processing_node(self):
        return self.now_processing_node

    def get_parent_nodes(self, node):
        parents = list(self.dag.predecessors(node))
        return parents

    def __str__(self):
        return self.as_subquestion_context_json()

    def _get_all_qa_str(self):
        def build_str_context(node: SearchTreeNode, rst_str:str):
            children = list(self.dag.successors(node))
            if not children:
                if node.answer is not None:
                    rst_str += f"question:{node.question},answer:{node.answer}"
                return rst_str
            children = sorted(children, key=lambda x: x.time_stamp)
            child_rst_str_list = []
            for child in children:
                child_rst_str = build_str_context(child, rst_str)
                child_rst_str_list.append(child_rst_str)
            if node.answer is not None:
                child_rst_str_list.append(f"question:{node.question},answer:{node.answer}")
            return "\n".join(child_rst_str_list)
        rst_str = ""
        return build_str_context(self.root_node, rst_str)

    def as_subquestion_context_json(self):
        """
        作为根节点的上下文
        """

        def build_tree_context(node: SearchTreeNode):
            children = list(self.dag.successors(node))
            if not children:
                if node.answer is not None:
                    return {f"{node.question}": [{"answer": f"{node.answer}"}]}
                elif node == self.get_now_processing_node():
                    return {f"{node.question}": [{"answer": "当前正在处理的子问题"}]}
                else:
                    return None
            children = sorted(children, key=lambda x: x.time_stamp)
            filtered_results = []
            for child in children:
                result = build_tree_context(child)
                if result is not None:
                    filtered_results.append(result)
            answer_str = node.answer
            if answer_str is None:
                answer_str = "等待子问题解答中"
            return {
                f"{node.question}": {
                    "answer": answer_str,
                    "children": filtered_results,
                }
            }

        context = f"Solution_Space_Tree:\n{json.dumps(build_tree_context(self.root_node),ensure_ascii=False,indent=2)}"
        return context

    def _graph_to_json(self):

        def build_tree(node):
            children = list(self.dag.successors(node))
            if not children:
                return {str(node): []}
            children = sorted(children, key=lambda x: x.time_stamp)
            return {str(node): [build_tree(child) for child in children]}

        return build_tree(self.root_node)

    def convert_to_pipleline(
        self, final_answer: str = None, final_answer_form_llm: bool = False
    ) -> CaPipeline:
        """
        转出思考树
        """
        pipeline = CaPipeline()
        pipeline.nodes = []
        pipeline.edges = []
        root_status = (
            ReporterIntermediateProcessTool.STATE.WAITING
            if self.now_plan is None
            else ReporterIntermediateProcessTool.STATE.RUNNING
        )
        if self.root_node.answer is not None:
            root_status = ReporterIntermediateProcessTool.STATE.FINISH
        pipeline.nodes.append(
            Node(
                id=self.id_allocator.allocate_root(
                    self.root_node.question + str(self.root_node.time_stamp)
                ),
                state=root_status,
                question=self.root_node.question,
                answer=self.root_node.answer,
                logs=None,
            )
        )

        def build_sub_nodes(node: SearchTreeNode):
            nonlocal pipeline
            children = list(self.dag.successors(node))
            if not children:
                return None
            children = sorted(children, key=lambda x: x.time_stamp)
            for child in children:
                tree_node: SearchTreeNode = child

                state = ReporterIntermediateProcessTool.STATE.WAITING
                if tree_node == self.now_processing_node:
                    state = ReporterIntermediateProcessTool.STATE.RUNNING
                if tree_node.answer is not None:
                    state = ReporterIntermediateProcessTool.STATE.FINISH
                pipeline.nodes.append(
                    Node(
                        id=self.id_allocator.allocate_id(
                            tree_node.question + str(tree_node.time_stamp)
                        ),
                        state=state,
                        question=tree_node.question,
                        answer=tree_node.answer,
                        logs=tree_node.answer_desc,
                        subgraph=tree_node.sub_graph if tree_node.sub_graph else None,
                    )
                )
                pipeline.edges.append(
                    Edge(
                        self.id_allocator.allocate_id(
                            node.question + str(node.time_stamp)
                        ),
                        self.id_allocator.allocate_id(
                            tree_node.question + str(tree_node.time_stamp)
                        ),
                    )
                )
                build_sub_nodes(child)

        build_sub_nodes(self.root_node)

        if final_answer is not None:
            answer_node = Node(
                id=0,
                state=ReporterIntermediateProcessTool.STATE.FINISH,
                question=self.root_node.question,
                answer=final_answer,
                logs="",
            )
            pipeline.nodes.append(answer_node)
            answer_edge = Edge(
                1 if final_answer_form_llm else self.id_allocator.get_max_id(),
                0,
            )
            pipeline.edges.append(answer_edge)

        return pipeline


class IDAllocator:
    def __init__(self):
        self.string_to_id = {}
        self.next_id = 2

    def allocate_root(self, root_str):
        self.string_to_id[root_str] = 1
        return 1

    def allocate_id(self, input_str):
        if input_str in self.string_to_id:
            return self.string_to_id[input_str]
        else:
            self.string_to_id[input_str] = self.next_id
            self.next_id += 1
            return self.string_to_id[input_str]

    def get_max_id(self):
        return self.next_id - 1
