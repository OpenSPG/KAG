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
    def __init__(
        self,
        executor: str,
        arguments: dict,
        parents: List = None,
        children: List = None,
    ):
        self.executor = executor
        self.arguments = arguments
        self.status = TaskStatus.PENDING
        self.id = str(uuid.uuid4())
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

    def add_parent(self, parent):
        print(f"add parent {parent.id} to {self.id}, total {len(self.parents)}")
        self.parents.append(parent)

    def add_child(self, child):
        self.children.append(child)

    def update_memory(self, key, value):
        self.memory[key] = value

    def update_result(self, result):
        self.result = result

    def __str__(self):
        msg = (
            f"Task<{self.id}>\nexecutor: {self.executor}\narguments {self.arguments}\n"
        )
        return msg

    __repr__ = __str__


Task.register("base", as_default=True)(Task)


class PlannerABC(Registrable):
    def __init__(self, executors, **kwargs):
        super().__init__(**kwargs)
        self.executors = executors

    @property
    def input_types(self):
        return str

    @property
    def output_types(self):
        return List[Task]

    def get_executor_by_name(self, name):
        for executor in self.executors:
            if executor.name == name:
                return executor
        return None

    def create_tasks_from_dag(self, task_dag: Dict[str, dict]):
        """create tasks from a dag, e.g. :
        {
            0: {
                "executor": "call_kg_retriever",
                "dependent_task_ids": [],
                "arguments": {"query": "张学友出演过的电影列表"},
            },
            1: {
                "executor": "call_kg_retriever",
                "dependent_task_ids": [],
                "arguments": {"query": "刘德华出演过的电影列表"},
            },
            2: {
                "executor": "call_py_code_generator",
                "dependent_task_ids": [0, 1],
                "arguments": {
                    "query": "请编写Python代码，找出以下两个列表的共同元素：\n张学友电影列表：{{0.output}}\n刘德华电影列表：{{1.output}}"
                },
            },
            3: {
                "executor": "call_deepseek",
                "dependent_task_ids": [2],
                "arguments": {"query": "请根据上下文信息，生成问题“张学友和刘德华共同出演过哪些电影”的详细答案"},
            },
        }
        """
        # create all Task objects
        task_map = {}
        for task_order, task_info in task_dag.items():
            print(f"task_info = {task_info}")
            task = Task(task_info["executor"], task_info["arguments"])
            task_map[task_order] = task
        for task_order, task_info in task_dag.items():
            deps = task_info["dependent_task_ids"]
            for dep in deps:
                print(f"{task_order} has parent {dep}")
                task_map[task_order].add_parent(task_map[dep])
                task_map[dep].add_child(task_map[task_order])

        return list(task_map.values())

    def invoke(self, query, **kwargs) -> List[Task]:
        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(self, query, **kwargs) -> List[Task]:
        raise NotImplementedError("ainvoke not implemented yet.")

    def decompose_task(self, task: Task, **kwargs) -> List[Task]:
        raise NotImplementedError("decompose_task not implemented yet.")

    def compose_task(self, task: Task, children_tasks: List[Task], **kwargs):
        raise NotImplementedError("compose_task not implemented yet.")

    def is_static(self):
        return True
