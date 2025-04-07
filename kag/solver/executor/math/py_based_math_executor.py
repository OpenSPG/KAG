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
import re
from typing import Optional

import subprocess
import sys
import tempfile

from tenacity import retry, stop_after_attempt

from kag.common.conf import KAG_PROJECT_CONF
from kag.common.parser.logic_node_parser import MathNode
from kag.interface import LLMClient, ExecutorABC, Task, Context
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.utils import init_prompt_with_fallback


def run_py_code(python_code: str, **kwargs):
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


@ExecutorABC.register("py_code_based_math_executor")
class PyBasedMathExecutor(ExecutorABC):
    def __init__(self, llm: LLMClient, tries: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
        self.tries = tries
        self.expression_builder = init_prompt_with_fallback(
            "expression_builder", KAG_PROJECT_CONF.biz_scene
        )

    @retry(stop=stop_after_attempt(3))
    def gen_py_code(self, query: str, context: str, error: str, **kwargs):
        return self.llm.invoke(
            {
                "question": query,
                "context": context,
                "error": error,
            },
            self.expression_builder,
            with_json_parse=False,
            **kwargs
        )


    def run_once(self, query: str, context: str, error: str, **kwargs):
        python_code = self.gen_py_code(query, context, error, **kwargs)
        if not python_code:
            raise RuntimeError("python code generate failed")

        code_result = run_py_code(python_code, **kwargs)
        return code_result

    def invoke(self, query: str, task: Task, context: Context, **kwargs):
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        logic_node = task.arguments.get("logic_form_node", None)
        task_query = task.arguments["query"]

        if logic_node and isinstance(logic_node, MathNode):
            kg_graph = context.variables_graph
            content = logic_node.content
            try:
                content_l = re.findall("`(.*?)`", content)
            except Exception as e:
                # breakpoint()
                content_l = []
            contents = []
            for c in content_l:
                if kg_graph.has_alias(c):
                    values = kg_graph.get_answered_alias(c)
                    if values:
                        c = str(values)
                    else:
                        continue
                contents.append(c)
            contents = "\n".join(contents) if contents else ""
        else:
            contents = ""


        self.report_content(
            reporter,
            "thinker",
            f"{task_query}_begin_task",
            task_query,
            "INIT",
            step=task.name,
            overwrite=False,
        )

        parent_results = []
        for pt in task.parents:
            parent_results.append(str(pt.result))

        parent_results = "\n".join(parent_results)

        parent_results += "\n" + contents
        tries = self.tries
        error = None


        while tries > 0:
            tries -= 1
            rst, error, code = self.run_once(task_query, parent_results, error, segment_name=f"{task_query}_begin_task", tag_name=f"{task_query}_code_generator", **kwargs)
            if rst is not None:
                result = f"""
                    ```{code}```
                    code result:{rst}
                    """
                task.update_result(result)
                self.report_content(
                    reporter, f"{task_query}_begin_task", f"{task_query}_end_math_executor_{task.id}", rst, "FINISH"
                )
                self.report_content(
                    reporter,
                    "thinker",
                    f"{task_query}_begin_task",
                    "finish",
                    "FINISH",
                    step=task.name,
                    overwrite=False,
                )
                if logic_node and isinstance(logic_node, MathNode):
                    context.variables_graph.add_answered_alias(logic_node.alias_name, rst)
                return result
            error = f"code:\n{code}\nerror:\n{error}"
        context.variables_graph.add_answered_alias(logic_node.alias_name, error)
        task.update_result(error)

        self.report_content(
            reporter, f"{task_query}_begin_task", f"{task_query}_end_math_executor_{task.id}", task.result, "FINISH"
        )
        self.report_content(
            reporter,
            "thinker",
            f"{task_query}_begin_task",
            "finish",
            "FINISH",
            step=task.name,
            overwrite=False,
        )

    def schema(self):
        return {
            "name": "Math",
            "description": "Used to address users' math or computational problems.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "The computable problem derived from the user's input question, retaining the essential information for the calculation target and dependencies.",
                    "optional": False,
                }
            },
        }
