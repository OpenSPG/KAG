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

from kag.common.parser.logic_node_parser import MathNode
from kag.interface import LLMClient, ExecutorABC, Task, Context, PromptABC
from kag.interface.solver.planner_abc import format_task_dep_context
from kag.interface.solver.reporter_abc import ReporterABC


def run_py_code(python_code: str, **kwargs):
    # Default timeout in seconds
    default_timeout = 5
    # Allow timeout to be passed via kwargs if needed for more flexibility
    timeout_duration = kwargs.get("timeout", default_timeout)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_file:
        temp_file.write(python_code.encode("utf-8"))
        temp_file_path = temp_file.name

    stdout_value = None
    stderr_value = None

    try:
        python_executable = sys.executable
        result = subprocess.run(
            [python_executable, temp_file_path],
            capture_output=True,
            text=True,
            timeout=timeout_duration,  # Added timeout
        )
        stdout_value = result.stdout
        stderr_value = result.stderr
    except subprocess.TimeoutExpired as e:
        stderr_value = f"Code execution timed out after {timeout_duration} seconds: {e}"
    except Exception as e:  # Catch other potential errors during subprocess.run
        stderr_value = f"An unexpected error occurred during code execution: {e}"
    finally:
        os.remove(temp_file_path)

    if stderr_value:  # If there's any error (timeout or other execution error)
        return None, stderr_value, python_code
    return stdout_value, None, python_code


@ExecutorABC.register("py_code_based_math_executor")
class PyBasedMathExecutor(ExecutorABC):
    def __init__(self, llm: LLMClient, tries: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
        self.tries = tries
        self.expression_builder = PromptABC.from_config(
            {"type": "default_expression_builder"}
        )

    @retry(stop=stop_after_attempt(3), reraise=True)
    def gen_py_code(self, query: str, context: str, error: str, **kwargs):
        return self.llm.invoke(
            {
                "question": query,
                "context": context,
                "error": error,
            },
            self.expression_builder,
            with_json_parse=False,
            **kwargs,
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
        tag_id = f"{task.arguments['query']}_begin_task"
        task_query = task.arguments.get("rewrite_query", task.arguments["query"])

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
                        c = f"{c}={values}"
                    else:
                        continue
                contents.append(c)
            contents = "input params:\n" + "\n".join(contents) if contents else ""
            math_query = f"{logic_node.sub_query}\n target:{logic_node.target}"
        else:
            contents = ""
            math_query = task_query

        self.report_content(
            reporter,
            "thinker",
            tag_id,
            f"{task_query}\n",
            "INIT",
            step=task.name,
        )

        parent_results = format_task_dep_context(task.parents)
        coder_content = context.kwargs.get("planner_thought", "") + "\n\n".join(
            parent_results
        )

        coder_content += "\n\n" + contents
        tries = self.tries
        error = None

        while tries > 0:
            tries -= 1
            rst, error, code = self.run_once(
                math_query,
                coder_content,
                error,
                segment_name=tag_id,
                tag_name=f"{task_query}_code_generator",
                **kwargs,
            )
            if rst is not None:
                if "i don't know" not in rst.lower():
                    result = f"""```python
{code}
```
code result:{logic_node.alias_name if logic_node else ""}={rst}"""
                    task.update_result(result)
                    self.report_content(
                        reporter,
                        tag_id,
                        f"{task_query}_end_math_executor_{task.id}",
                        rst,
                        "FINISH",
                    )
                    self.report_content(
                        reporter,
                        "thinker",
                        tag_id,
                        "",
                        "FINISH",
                        step=task.name,
                        overwrite=False,
                    )
                    if logic_node and isinstance(logic_node, MathNode):
                        context.variables_graph.add_answered_alias(
                            logic_node.alias_name, rst
                        )
                    return result
                if tries > 0:
                    error = f"Please retry with: Best-effort code generation using analogous implementations or educated-guess fallbacks where needed."
                else:
                    error = rst
            error = f"""code:
```python
{code}
```
error:
{error}"""

        context.variables_graph.add_answered_alias(logic_node.alias_name, error)
        task.update_result(error)

        self.report_content(
            reporter,
            f"{task_query}_begin_task",
            f"{task_query}_end_math_executor_{task.id}",
            error,
            "FINISH",
        )
        self.report_content(
            reporter,
            "thinker",
            f"{task_query}_begin_task",
            "",
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
