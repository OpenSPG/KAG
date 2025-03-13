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
from collections import OrderedDict
from kag.interface.solver.planner_abc import Task
from kag.common.registry import Registrable


class Context:
    """Pipeline execution context that tracks tasks and their dependencies."""

    def __init__(self):
        """Initializes an ordered dictionary to store tasks in insertion order."""

        self._tasks = OrderedDict()

    def add_task(self, task: Task):
        """Adds a task to the context.

        Args:
            task: Task instance to be added to the execution context.
        """
        self._tasks[task.id] = task

    def last_task(self):
        """Retrieves the most recently added task.

        Returns:
            The last task in the execution order, or None if no tasks exist.
        """
        if len(self._tasks) == 0:
            return None
        last_id = list(self._tasks.keys())[-1]
        return self._tasks[last_id]

    def append_task(self, task: Task):
        """Appends a new task and automatically sets its parent to the last task.

        Used for iterative planning where new tasks depend on the latest execution state.
        Automatically adds parent dependency only if the task has no existing parents.

        Args:
            task: Task to append to the execution sequence.
        """
        if len(task.parents) == 0 and len(self._tasks) > 0:
            task.parents = [self.last_task()]
        self.add_task(task)

    def get_task(self, task_id: str):
        """Retrieves a task by its unique identifier.

        Args:
            task_id: Unique identifier of the task to retrieve.

        Returns:
            The requested task if found, otherwise None.
        """
        return self._tasks.get(task_id)

    def topological_sort(self, dag: nx.DiGraph):
        """Performs topological sort on a directed acyclic graph (DAG).

        Args:
            dag: NetworkX graph representing task dependencies.

        Returns:
            Generator yielding node IDs in topological order.
        """
        return nx.topological_sort(dag)

    def topological_generations(self, dag: nx.DiGraph):
        """Generates topological generations (parallelizable task groups).

        Args:
            dag: NetworkX graph representing task dependencies.

        Returns:
            Generator yielding lists of node IDs that can be executed in parallel.
        """
        return nx.topological_generations(dag)

    def get_dag(self):
        """Constructs a directed acyclic graph (DAG) of task dependencies.

        Verifies all referenced tasks exist in the context. Raises ValueError if any
        dependency references a non-existent task.

        Returns:
            A NetworkX DiGraph representing the task dependency structure.

        Raises:
            ValueError: If a task referenced in dependencies does not exist.
        """
        dag = nx.DiGraph()
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
                dag.add_edge(dep.id, task_id)
        self.topological_sort(dag)
        return dag

    def gen_task(self, group: bool = False):
        """Generates tasks in execution order, optionally grouped by parallelizable stages.

        Args:
            group: If True, yields lists of tasks that can be executed in parallel.
                   If False (default), yields individual tasks sequentially.

        Returns:
            Generator yielding either individual Task objects or lists of Tasks,
            depending on the 'group' parameter.

        Raises:
            NetworkXUnfeasible: If the task dependency graph contains cycles.
        """
        dag = self.get_dag()
        if not group:
            nodes = self.topological_sort(dag)
            for node in nodes:
                yield self._tasks[node]
        else:
            node_groups = self.topological_generations(dag)
            for node_group in node_groups:
                yield [self._tasks[node] for node in node_group]


class SolverPipelineABC(Registrable):
    """Base class for solver pipelines.

    This abstract base class defines the interface for solver pipeline implementations.
    Subclasses must implement the `invoke` and `ainvoke` methods to provide concrete
    execution logic.
    """

    def __init__(self):
        """Initializes the solver pipeline base class."""
        pass

    def invoke(self, query, **kwargs):
        """Executes the solver pipeline synchronously.

        Args:
            query: Input query or data to be processed by the pipeline.
            **kwargs: Additional keyword arguments for pipeline execution.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(self, query, **kwargs):
        """Executes the solver pipeline asynchronously.

        Args:
            query: Input query or data to be processed by the pipeline.
            **kwargs: Additional keyword arguments for pipeline execution.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("ainvoke not implemented yet.")
