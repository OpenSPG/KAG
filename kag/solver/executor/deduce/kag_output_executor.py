import json
import logging


from typing import Any, Optional

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.common.config import get_default_chat_llm_config
from kag.common.parser.logic_node_parser import GetNode
from kag.interface import ExecutorABC, LLMClient, PromptABC, Context
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.utils import init_prompt_with_fallback

logger = logging.getLogger()


def convert_result_2_md(result, is_top=False):
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        out = []
        for r in result:
            if is_top:
                out.append(f"- {convert_result_2_md(result=r)}")
            else:
                out.append(f"、{convert_result_2_md(result=r)}")
        return "\n".join(out)
    if isinstance(result, dict):
        return f"""```json
    {json.dumps(result, ensure_ascii=False, indent=2)}
    ```"""
    else:
        return str(result)


@ExecutorABC.register("kag_output_executor")
class KagOutputExecutor(ExecutorABC):
    """Hybrid knowledge graph retrieval executor combining multiple strategies.

    Combines entity linking, path selection, and text chunk retrieval using
    knowledge graph and LLM capabilities to answer complex queries.
    """

    def __init__(
        self, llm_module: LLMClient = None, summary_prompt: PromptABC = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.llm_module = llm_module or LLMClient.from_config(
            get_default_chat_llm_config()
        )
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.summary_prompt = summary_prompt or init_prompt_with_fallback(
            "output_question", kag_project_config.biz_scene
        )

    @property
    def output_types(self):
        """Output type specification for executor responses"""
        return str

    def invoke(self, query: str, task: Any, context: Context, **kwargs):
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        task_query = task.arguments["query"]
        logic_node = task.arguments.get("logic_form_node", None)
        self.report_content(
            reporter,
            "thinker",
            f"{task_query}_begin_task",
            f"{task_query}\n",
            "INIT",
            step=task.name,
        )
        if not logic_node or not isinstance(logic_node, GetNode):
            self.report_content(
                reporter,
                "thinker",
                f"{task_query}_begin_task",
                "not implement!",
                "FINISH",
                overwrite=False,
                step=task.name,
            )
            return
        result = []
        for alias in logic_node.alias_name_set:
            if context.variables_graph.has_alias(alias.alias_name):
                alias_answer = context.variables_graph.get_answered_alias(
                    alias.alias_name
                )
                if alias_answer:
                    result.append(alias_answer)
        if not result:
            dep_context = []
            for p in task.parents:
                dep_context.append(p.get_task_context())
            result = self.llm_module.invoke(
                {"question": query, "context": dep_context},
                self.summary_prompt,
                with_json_parse=False,
                segment_name=f"{task_query}_begin_task",
                tag_name=f"{task_query}_output",
                **kwargs,
            )
        self.report_content(
            reporter,
            "thinker",
            f"{task_query}_begin_task",
            "",
            "FINISH",
            overwrite=False,
            step=task.name,
        )
        task.update_result(result)

    def schema(self) -> dict:
        """Function schema definition for OpenAI Function Calling

        Returns:
            dict: Schema definition in OpenAI Function format
        """
        return {
            "name": "Output",
            "description": "Output answer from knowledge.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query for answer.",
                    "optional": False,
                },
            },
        }
