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
from typing import Optional

from kag.common.utils import extract_box_answer
from kag.interface import GeneratorABC, LLMClient, PromptABC
from kag.interface.solver.reporter_abc import ReporterABC


def to_task_context_str(context):
    if not context or "task" not in context:
        return ""
    return f"""{context['name']}: {context['task']}
#{context['name'].lower().replace("step", "")}:{context['result']}"""


def extra_reference(references):
    return [
        {
            "content": reference["content"],
            "document_name": reference["document_name"],
            "id": reference["id"],
        }
        for reference in references
    ]


@GeneratorABC.register("kag_model_generator")
class KagModelGenerator(GeneratorABC):
    def __init__(
        self,
        llm_client: LLMClient,
        generate_answer_prompt: PromptABC,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_client = llm_client
        self.generate_answer_prompt = generate_answer_prompt

    def invoke(self, query, context, **kwargs):
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        results = []
        tasks = []
        last_question = query
        for task in context.gen_task(False):
            tasks.append(task)
            if task.executor != "Output":
                task_result = to_task_context_str(task.get_task_context())
                if task_result:
                    results.append(task_result)
        if tasks[-1].executor == "Output":
            last_question = tasks[-1].arguments.get(
                "origin_query", tasks[-1].arguments["query"]
            )
        messages = context.kwargs.get("messages", [])
        messages.append(
            {
                "role": "user",
                "content": self.generate_answer_prompt.build_prompt(
                    {
                        "last_question": last_question,
                        "sub_questions": "\n".join(results),
                        "question": query,
                    }
                ),
            }
        )

        summary_response = self.llm_client.__call__(
            prompt="",
            messages=messages,
            segment_name="answer",
            tag_name="Final Answer",
            reporter=reporter,
        )
        summary_response = extract_box_answer(summary_response)
        messages.append(
            {
                "role": "assistant",
                "content": summary_response,
            }
        )
        if reporter:
            reporter.add_report_line("generator", "task_process", messages, "FINISH")
        return summary_response
