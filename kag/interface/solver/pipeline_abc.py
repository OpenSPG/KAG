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
import networkx as nx
from typing import Any
from collections import OrderedDict
from kag.interface.solver.planner import Task
from kag.common.registry import Registrable


class Context:
    def __init__(self):
        self._tasks = OrderedDict()
        self._memory = OrderedDict()

    def add_task(self, task: Task):
        self._tasks[task.id] = task

    def last_task(self):
        if len(self._tasks) == 0:
            return None
        last_id = list(self._tasks.keys())[-1]
        return self._tasks[last_id]

    def append_task(self, task: Task):
        # append a new task and set it's parent to last task
        # used for iterative planning
        if len(task.parents) == 0 and len(self._tasks) > 0:
            task.parents = [self.last_task]
        self.add_task(task)

    def get_task(self, task_id):
        return self._tasks.get(task_id)

    def get_memory(self, task_id):
        return self._memory.get(task_id)

    def set_memory(self, task_id, memory: Any):
        self._memory[task_id] = memory

    def topological_sort(self, dag: nx.Graph):
        return nx.topological_sort(dag)

    def topological_generations(self, dag: nx.Graph):
        return nx.topological_generations(dag)

    def get_dag(self):
        dag = nx.Graph()
        nodes = set()
        for task_id, task in self._tasks.items():
            nodes.add(task_id)
            for dep in task.parents:
                nodes.add(dep.id)
        for node in nodes:
            if node not in self._tasks:
                raise ValueError(f"task {node} not found.")
        dag.add_nodes_from(nodes)
        for task_id, task in self._tasks.items():
            for dep in task.parents:
                dag.add_edge(task_id, dep.id)
        self.topological_sort(dag)
        return dag

    def gen_task(self, group: bool = False):
        dag = self.get_dag()
        if group:
            nodes = self.topological_sort(dag)
            for node in nodes:
                yield self._tasks[node]
        else:
            node_groups = self.topological_generations(dag)
            for node_group in node_groups:
                yield [self._tasks[node] for node in node_group]


class SolverPipelineABC(Registrable):
    def __init__(self):
        pass

    def invoke(self, query, **kwargs):
        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(self, query, **kwargs):
        raise NotImplementedError("ainvoke not implemented yet.")
