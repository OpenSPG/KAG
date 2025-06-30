import logging
import re

from typing import Any, Optional

from kag.common.config import get_default_chat_llm_config
from kag.common.parser.logic_node_parser import DeduceNode
from kag.interface import ExecutorABC, LLMClient, PromptABC, Context
from kag.interface.solver.reporter_abc import ReporterABC

logger = logging.getLogger()


@ExecutorABC.register("kag_deduce_executor")
class KagDeduceExecutor(ExecutorABC):
    """Hybrid knowledge graph retrieval executor combining multiple strategies.

    Combines entity linking, path selection, and text chunk retrieval using
    knowledge graph and LLM capabilities to answer complex queries.
    """

    def __init__(
        self,
        llm_module: LLMClient = None,
        deduce_choice_prompt: PromptABC = None,
        deduce_entail_prompt: PromptABC = None,
        deduce_extractor_prompt: PromptABC = None,
        deduce_judge_prompt: PromptABC = None,
        deduce_multi_choice_prompt: PromptABC = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_module = llm_module or LLMClient.from_config(
            get_default_chat_llm_config()
        )
        self.deduce_choice_prompt = deduce_choice_prompt or PromptABC.from_config(
            {"type": "default_deduce_choice"}
        )
        self.deduce_entail_prompt = deduce_entail_prompt or PromptABC.from_config(
            {"type": "default_deduce_entail"}
        )
        self.deduce_extractor_prompt = deduce_extractor_prompt or PromptABC.from_config(
            {"type": "default_deduce_extractor"}
        )
        self.deduce_judge_prompt = deduce_judge_prompt or PromptABC.from_config(
            {"type": "default_deduce_judge"}
        )
        self.deduce_multi_choice_prompt = (
            deduce_multi_choice_prompt
            or PromptABC.from_config({"type": "default_deduce_multi_choice"})
        )

        self.prompt_mapping = {
            "choice": self.deduce_choice_prompt,
            "multiChoice": self.deduce_multi_choice_prompt,
            "entailment": self.deduce_entail_prompt,
            "judgement": self.deduce_judge_prompt,
            "extract": self.deduce_extractor_prompt,
        }

    @property
    def output_types(self):
        """Output type specification for executor responses"""
        return str

    def call_op(self, sub_query, contents, op, **kwargs):
        if op not in self.prompt_mapping:
            op = "entailment"
        prompt = self.prompt_mapping.get(op, self.deduce_entail_prompt)

        return self.llm_module.invoke(
            {"instruction": sub_query, "memory": contents},
            prompt,
            with_json_parse=False,
            with_except=True,
            tag_name=f"{sub_query}_deduce_{op}",
            **kwargs,
        )

    def invoke(self, query: str, task: Any, context: Context, **kwargs):
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        tag_id = f"{task.arguments['query']}_begin_task"
        task_query = task.arguments.get("rewrite_query", task.arguments["query"])
        logic_node = task.arguments.get("logic_form_node", None)
        self.report_content(
            reporter,
            "thinker",
            tag_id,
            f"{task_query}\n",
            "INIT",
            step=task.name,
        )
        if not logic_node or not isinstance(logic_node, DeduceNode):
            self.report_content(
                reporter,
                tag_id,
                f"{task_query}_deduce",
                "not implement!",
                "FINISH",
                step=task.name,
                overwrite=False,
            )
            return
        deduce_query = f"{logic_node.sub_query}\ntarget:{logic_node.target}"
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
                    c = f"{c}={str(values)}"
                else:
                    continue
            contents.append(c)
        contents = "\ninput information:\n" + "\n".join(contents) if contents else ""

        for k, v in context.kwargs.get("step_answer", {}).items():
            if k in task_query:
                contents += f"\n{k}={v}\n"

        result = []
        final_if_answered = False
        for op in logic_node.ops:
            if_answered, answer = self.call_op(
                deduce_query, contents, op, segment_name=tag_id, **kwargs
            )
            result.append(answer)
            final_if_answered = if_answered or final_if_answered
        res = ";".join(result)
        context.variables_graph.add_answered_alias(
            logic_node.alias_name, f"{task_query}\n{res}"
        )
        task.update_result(res)

        self.report_content(
            reporter,
            "thinker",
            tag_id,
            "",
            "FINISH",
            step=task.name,
            overwrite=False,
        )

    def schema(self) -> dict:
        """Function schema definition for OpenAI Function Calling

        Returns:
            dict: Schema definition in OpenAI Function format
        """
        return {
            "name": "Deduce",
            "description": "Deduce answer from context or llm knowledge",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query for answer.",
                    "optional": False,
                },
            },
        }
