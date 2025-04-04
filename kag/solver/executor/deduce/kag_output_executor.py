
import logging


from typing import Any, Optional

from kag.common.config import get_default_chat_llm_config
from kag.common.parser.logic_node_parser import GetNode
from kag.interface import ExecutorABC, LLMClient, PromptABC, Context
from kag.interface.solver.reporter_abc import ReporterABC

logger = logging.getLogger()


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
        self.summary_prompt = summary_prompt

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
            task_query,
            "FINISH",
            step=task.name
        )
        if not logic_node or not isinstance(logic_node, GetNode):
            self.report_content(
                reporter,
                "thinker",
                f"{task_query}_output",
                "not implement!",
                "FINISH",
                step=task.name
            )
            return
        result = context.variables_graph.get_answered_alias(logic_node.alias_name.alias_name)
        if isinstance(result, list):
            result = "\n".join(result)
        self.report_content(
            reporter,
            "thinker",
            f"{task_query}_output",
            "finish",
            "FINISH",
            step=task.name
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
