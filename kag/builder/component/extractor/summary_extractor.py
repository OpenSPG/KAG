import logging
from typing import List

from kag.builder.prompt.utils import init_prompt_with_fallback
from kag.common.conf import KAG_PROJECT_CONF
from kag.common.config import get_default_chat_llm_config
from kag.interface import ExtractorABC, LLMClient, PromptABC

from kag.builder.model.chunk import Chunk
from kag.builder.model.sub_graph import SubGraph
from knext.schema.client import CHUNK_TYPE
from knext.common.base.runnable import Input, Output

logger = logging.getLogger(__name__)

@ExtractorABC.register("summary_extractor")
class SummaryExtractor(ExtractorABC):
    def __init__(self, llm_module: LLMClient = None, chunk_summary_prompt: PromptABC = None):
        super().__init__()
        self.llm_module = llm_module or LLMClient.from_config(
            get_default_chat_llm_config()
        )
        self.chunk_summary_prompt = chunk_summary_prompt or init_prompt_with_fallback(
            "chunk_summary", KAG_PROJECT_CONF.biz_scene
        )

    @property
    def input_types(self):
        return Chunk

    @property
    def output_types(self):
        return [SubGraph]

    @property
    def inherit_input_key(self):
        return True

    @staticmethod
    def output_indices() -> List[str]:
        return ["Summary"]

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the semantic extractor to process input data.

        Args:
            input (Input): Input data containing name and content.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of processed results, containing subgraph information.
        """
        if "/" not in input.name:
            summary_name = input.name
        else:
            summary_name = input.name.split("/")[-1]

        index = summary_name.find("_split")
        if index != -1:
            summary_name = summary_name[:index]

        content = input.content
        summary = self.llm_module.invoke(
            {"content": content}, self.chunk_summary_prompt, with_json_parse=False
        )


        sub_graph = SubGraph([],[])
        # add Summary Node
        sub_graph.add_node(
            id=input.id,
            name=summary_name,
            label="Summary",
            properties = {
                "id": input.id,
                "name": summary_name,
                "content": summary,
            }
        )

        parent_id = getattr(input, "parent_id", None)
        if parent_id is not None:
            # add Summary_childOf_Summary edge
            sub_graph.add_edge(
                s_id=input.id,
                s_label="Summary",
                p="childOf",
                o_id=parent_id,
                o_label="Summary",
                properties = {}
            )

        # add Summary_relateTo_Chunk edge
        sub_graph.add_edge(
            s_id=input.id,
            s_label="Summary",
            p="relateTo",
            o_id=f"{input.id}_{input.name}",
            o_label=CHUNK_TYPE,
            properties = {}
        )

        return [sub_graph]
