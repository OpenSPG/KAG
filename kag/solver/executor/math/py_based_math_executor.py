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

import os
import asyncio
import aiofiles
import subprocess
import sys
import tempfile

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import LLMClient, ExecutorABC, Task, Context
from kag.solver.utils import init_prompt_with_fallback


@ExecutorABC.register("py_code_based_math_executor")
class PyBasedMathExecutor(ExecutorABC):
    def __init__(self, llm: LLMClient, tries: int = 3, **kwargs):
        self.llm = llm
        self.tries = tries
        self.expression_builder = init_prompt_with_fallback(
            "expression_builder", KAG_PROJECT_CONF.biz_scene
        )

    async def agen_py_code(self, query: str, context: str, error: str):
        python_code = await self.llm.ainvoke(
            {
                "question": query,
                "context": context,
                "error": error,
            },
            self.expression_builder,
            with_json_parse=False,
        )
        print(f"python_code = {python_code}")
        return python_code

    async def arun_py_code(self, python_code: str):
        temp_file = None
        stdout = None
        stderr = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as sync_temp:
                temp_file_path = sync_temp.name

            async with aiofiles.open(temp_file_path, "wb") as temp_file:
                await temp_file.write(python_code.encode("utf-8"))
                await temp_file.flush()

            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                temp_file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        if len(stderr) > 0:
            return None, stderr, python_code
        return stdout, None, python_code

    async def arun_once(self, query: str, context: str, error: str):
        python_code = await self.agen_py_code(query, context, error)
        if not python_code:
            raise RuntimeError("python code generate failed")

        code_result = await self.arun_py_code(python_code)
        return code_result

    async def ainvoke(self, query: str, task: Task, context: Context, **kwargs):
        task_query = task.arguments["query"]
        parent_results = []
        for pt in task.parents:
            parent_results.append(str(pt.result))

        parent_results = "\n".join(parent_results)
        tries = self.tries
        error = None
        while tries > 0:
            tries -= 1
            rst, error, code = await self.arun_once(task_query, parent_results, error)
            if rst is not None:
                return rst
            error = f"code:\n{code}\nerror:\n{error}"
        return "I don't know"

    def gen_py_code(self, query: str, context: str, error: str):
        python_code = self.llm.invoke(
            {
                "question": query,
                "context": context,
                "error": error,
            },
            self.expression_builder,
            with_json_parse=False,
        )
        print(f"python_code = {python_code}")
        return python_code

    def run_py_code(self, python_code: str):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_file:
            temp_file.write(python_code.encode("utf-8"))
            temp_file_path = temp_file.name

        try:
            python_executable = sys.executable
            result = subprocess.run(
                [python_executable, temp_file_path], capture_output=True, text=True
            )
        finally:
            os.remove(temp_file_path)

        stdout_value = result.stdout
        stderr_value = result.stderr
        if len(stderr_value) > 0:
            return None, stderr_value, python_code
        return stdout_value, None, python_code

    def run_once(self, query: str, context: str, error: str):
        python_code = self.gen_py_code(query, context, error)
        if not python_code:
            raise RuntimeError("python code generate failed")

        code_result = self.run_py_code(python_code)
        return code_result

    def invoke(self, query: str, task: Task, context: Context, **kwargs):
        task_query = task.arguments["query"]
        parent_results = []
        for pt in task.parents:
            parent_results.append(str(pt.result))

        parent_results = "\n".join(parent_results)
        tries = self.tries
        error = None
        while tries > 0:
            tries -= 1
            rst, error, code = self.run_once(task_query, parent_results, error)
            if rst is not None:
                return rst
            error = f"code:\n{code}\nerror:\n{error}"
        return "I don't know"

    def schema(self):
        return {
            "name": "Math",
            "description": "Used to address users' math or computational problems. The user's question is first transformed into executable Python code, which is then executed to return the result.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User input math or computational problem and will be transformed into Python code for execution.",
                    "optional": False,
                }
            },
        }
