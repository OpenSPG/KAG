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
import uuid
from enum import Enum
from typing import List, Dict
from kag.common.registry import Registrable


class TaskStatus(Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Task(Registrable):
    """Represents an executable task that can be processed by an executor.

    Attributes:
        executor (str): Name of the executor responsible for running this task.
        arguments (dict): Parameters required for task execution.
        status (TaskStatus): Current execution status of the task (PENDING by default).
        id (str): Unique identifier generated using UUID.
        parents (List[Task]): List of predecessor tasks that must complete before execution.
        children (List[Task]): List of successor tasks that depend on this task's completion.
        memory (dict): Storage for intermediate execution data.
        result (Any): Final output of the task execution.
    """

    def __init__(
        self,
        executor: str,
        arguments: dict,
        parents: List = None,
        children: List = None,
        id: str = None,
        **kwargs,
    ):
        """Represents an executable task that can be processed by an executor.

        Attributes:
            executor (str): Name of the executor responsible for running this task.
            arguments (dict): Parameters required for task execution.
            status (TaskStatus): Current execution status of the task (PENDING by default).
            id (str): Unique identifier.
            parents (List[Task]): List of predecessor tasks that must complete before execution.
            children (List[Task]): List of successor tasks that depend on this task's completion.
            memory (dict): Storage for intermediate execution data.
            result (Any): Final output of the task execution.
        """
        super().__init__(**kwargs)
        self.executor = executor
        self.arguments = arguments
        self.thought = kwargs.get("thought", "")
        self.status = TaskStatus.PENDING
        if id is None:
            self.id = str(uuid.uuid4())
        else:
            self.id = id
        if parents is None:
            self.parents = []
        else:
            self.parents = parents
        if children is None:
            self.children = []
        else:
            self.children = children

        self.memory = {}
        self.result = None

        self.name = kwargs.get("name", None) or str(self.id)

    def add_parent(self, parent):
        """Adds a predecessor task to the dependency list.

        Args:
            parent: Task object that must complete before this task can execute.
        """
        self.parents.append(parent)

    def add_child(self, child):
        """Adds a successor task to the dependency list.

        Args:
            child: Task object that depends on this task's completion.
        """
        self.children.append(child)

    def update_memory(self, key, value):
        """Stores intermediate data during task execution.

        Args:
            key: Identifier for the stored data.
            value: Data value to be stored in task memory.
        """
        self.memory[key] = value

    def update_result(self, result):
        """Sets the final result of the task execution.

        Args:
            result: Output value produced by the task.
        """
        self.result = result

    def get_task_context(self, with_all=False):
        """Generates a dictionary representation of the task's context."""
        result = {}
        if self.thought:
            result["thought"] = self.thought
        if self.result:
            if isinstance(self.result, str):
                result["result"] = self.result
            elif hasattr(self.result, "summary"):
                summary = getattr(self.result, "summary", "")
                if summary and (with_all or "i don't know" not in summary.lower()):
                    result["result"] = summary
            else:
                result["result"] = str(self.result)

        if result:
            result["task"] = self.arguments.get(
                "rewrite_query", self.arguments.get("query", "")
            )

        if self.name:
            result["name"] = self.name
        return result

    def __str__(self):
        """Generates a string representation of the task.

        Returns:
            Formatted string containing task ID, executor name, and arguments.
        """
        msg = f"Task<{self.id}>\n\texecutor: {self.executor}\n\targuments {self.arguments}\n"
        return msg

    __repr__ = __str__

    @staticmethod
    def create_tasks_from_dag(task_dag: Dict[str, dict]):
        """Constructs task objects from a task dependency graph definition.

        Example DAG format:
        {
            "0": {
                "executor": "call_kg_retriever",
                "dependent_task_ids": [],
                "arguments": {"query": "张学友出演过的电影列表"},
            },
            "1": {
                "executor": "call_kg_retriever",
                "dependent_task_ids": ["0"],
                "arguments": {"query": "刘德华出演过的电影列表"},
            },
        }

        Args:
            task_dag: Dictionary where keys are task IDs and values contain:
                - executor: Name of the task executor
                - dependent_task_ids: List of prerequisite task IDs
                - arguments: Execution parameters for the task

        Returns:
            List of Task objects with established parent/child relationships.
        """

        task_map = {}
        for task_order, task_info in task_dag.items():
            task = Task(
                task_info["executor"],
                task_info["arguments"],
                id=task_order,
                thought=task_info.get("thought", ""),
                name=task_info.get("name", None),
            )
            task_map[task_order] = task
        for task_order, task_info in task_dag.items():
            deps = task_info["dependent_task_ids"]
            for dep in deps:
                task_map[task_order].add_parent(task_map[dep])
                task_map[dep].add_child(task_map[task_order])

        return list(task_map.values())


class PlannerABC(Registrable):
    """Abstract base class for task planners that generate execution workflows.

    Planners are responsible for creating Directed Acyclic Graphs (DAGs) of tasks
    based on user query.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def input_types(self):
        return str

    @property
    def output_types(self):
        return List[Task]

    def invoke(self, query, **kwargs) -> List[Task]:
        """Synchronously creates an execution plan from the given query.

        Args:
            query: User input/query to generate the plan for
            **kwargs: Additional execution parameters

        Returns:
            List of Tasks representing the execution plan

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """

        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(self, query, **kwargs) -> List[Task]:
        """Asynchronously creates an execution plan from the given query.

        Args:
            query: User input/query to generate the plan for
            **kwargs: Additional execution parameters

        Returns:
            List of Tasks representing the execution plan

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """

        raise NotImplementedError("ainvoke not implemented yet.")

    def decompose_task(self, task: Task, **kwargs) -> List[Task]:
        """Breaks down a complex task into simpler sub-tasks.

        Args:
            task: Parent task to decompose
            **kwargs: Additional decomposition parameters

        Returns:
            List of child tasks implementing the decomposition

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """

        raise NotImplementedError("decompose_task not implemented yet.")

    def compose_task(self, task: Task, children_tasks: List[Task], **kwargs):
        """Combines results from child tasks into the parent task.

        Args:
            task: Parent task to receive composed results
            children_tasks: List of completed child tasks
            **kwargs: Additional composition parameters

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """

        raise NotImplementedError("compose_task not implemented yet.")

    def is_static(self):
        """Indicates if the planner uses static or iterative task decomposition.

        Returns:
            True if the planner uses static task decomposition, False if iteratively.
        """

        return True

    async def finish_judger(self, query: str, answer: str):
        return True


def format_task_dep_context(tasks: List[Task], is_recu=True):
    """Formats parent task execution context into a structured dictionary.

    Args:
        task (Task): Current task whose parent context needs formatting

    Returns:
        dict: Mapping of parent task IDs to their execution details containing:
            - action: Executor and arguments used
            - result: Execution result of the parent task
    """

    def to_str(context):
        if not context or "task" not in context:
            return ""
        return f"""{context['name']}:{context['task']}
{context['result']}.{context.get('thought', '')}"""

    if not tasks:
        return []
    formatted_context = []
    if isinstance(tasks, Task):
        tasks = [tasks]
    for task in tasks:
        # get all prvious tasks from context.
        if is_recu:
            parent_res = format_task_dep_context(task.parents, is_recu)
            for p in parent_res:
                if p not in formatted_context:
                    formatted_context.append(p)
        res = to_str(task.get_task_context(with_all=True))

        if res:
            if res in formatted_context:
                continue
            formatted_context.append(res)
    return formatted_context
