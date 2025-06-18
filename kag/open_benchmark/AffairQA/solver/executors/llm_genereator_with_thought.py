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
# flake8: noqa
import json
from kag.interface import GeneratorABC, LLMClient, PromptABC
from kag.interface.solver.base_model import Identifier
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_hybrid_executor import (
    to_reference_list,
)


@GeneratorABC.register("llm_generator_with_thought")
class LLMGeneratorWithThought(GeneratorABC):
    def __init__(
        self,
        llm_client: LLMClient,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_client = llm_client

    def invoke(self, query, context, **kwargs):
        rerank_queries = []
        chunks = []
        thoughts = []
        refer_data = ""
        refer_data_graph = context.variables_graph._graph_to_json()

        def serialize_object(obj):
            if isinstance(obj, Identifier):
                return str(obj)
            elif isinstance(obj, dict):
                return {
                    serialize_object(k): serialize_object(v) for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [serialize_object(item) for item in obj]
            elif isinstance(obj, tuple):
                return tuple(serialize_object(item) for item in obj)
            elif isinstance(obj, set):
                return {serialize_object(item) for item in obj}
            else:
                return obj

        refer_data_graph = serialize_object(refer_data_graph)
        # 截断图数据，避免超过长度限制
        refer_data_graph_str = json.dumps(refer_data_graph, ensure_ascii=False)
        if len(refer_data_graph_str) > 20000:
            refer_data_graph_str = refer_data_graph_str[:20000] + "..."
        refer_data_graph = refer_data_graph_str

        thoughts = "\n\n".join(thoughts)
        refer_data = refer_data + "\n\n" + refer_data_graph

        system_instruction = """
作为高级阅读理解助手，您的任务是根据我提供的上下文来回答复杂的多跳问题。我提供的上下文包括两部分：一组有助于回答问题的文档，以及对问题的逐步分解和分析思考过程。请结合这两部分上下文来回答问题。您的回答应在"思考过程:"之后开始，在这里您将有条不紊地、一步步地分解推理过程，说明您是如何得出结论的。最后以"答案:"结尾，给出一个简洁、明确的回答，无需额外阐述。\n
注意：
1. 我希望您的答案与标准答案完全匹配，因此请确保"答案:"后面的回答简洁明了，例如"1832年5月14日"或"是"。越短越好！！
2. 如果答案是日期，请尽可能提供完整日期，例如"1932年5月18日"。
3. 请注意词性的差异，例如"日本"和"日本的"，并根据问题的要求提供准确的格式。
4  不要在意里面是否有暗示你答案存不存在，你需要根据所有的文本自己判断，不要听它告诉你是否有答案。
5. 如果您认为提供的文档无法回答该问题，请回答"答案: UNKNOWN"。
6. 尽量以Docs中的内容为准
"""

        prompt = f"{system_instruction}\n\nDocs:\n{refer_data}\nStep by Step Analysis:\n{thoughts}Question: {query}"

        try:
            response = self.llm_client(prompt)
        except Exception as e:
            # save prompt to file in the same directory
            import os

            current_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(current_dir, "prompt.txt"), "a") as f:
                f.write(prompt)
            raise e

        if (
            "答案: " not in response
            and "答案:" not in response
            and "answer: " not in response
            and "answer:" not in response
        ):
            raise ValueError(f"no answer found in response: {response}")
        # Extract answer from response, handling different possible formats
        if "答案: " in response:
            answer = response.split("答案: ")[1].strip()
        elif "答案:" in response:
            answer = response.split("答案:")[1].strip()
        elif "answer: " in response:
            answer = response.split("answer: ")[1].strip()
        elif "answer:" in response:
            answer = response.split("answer:")[1].strip()
        else:
            # This should not happen due to the check above, but just in case
            answer = response.strip()
        return answer
