import logging
from typing import List

from kag.interface import ExtractorABC

from kag.builder.model.chunk import Chunk
from kag.builder.model.sub_graph import SubGraph
from kag.interface.common.model.chunk import ChunkTypeEnum
from knext.schema.client import CHUNK_TYPE, TABLE_TYPE
from knext.common.base.runnable import Input, Output

logger = logging.getLogger(__name__)


@ExtractorABC.register("outline_extractor")
class OutlineExtractor(ExtractorABC):
    def __init__(self):
        super().__init__()

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
        return ["outline_index"]

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the semantic extractor to process input data.

        Args:
            input (Input): Input data containing name and content.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of processed results, containing subgraph information.
        """
        if input.type == ChunkTypeEnum.Text:
            o_label = CHUNK_TYPE
        else:
            o_label = TABLE_TYPE
        # if "/" not in input.name:
        outline_name = input.name
        # else:
        #     outline_name = input.name.split("/")[-1]

        index = outline_name.find("_split")
        if index != -1:
            outline_name = outline_name[:index]

        sub_graph = SubGraph([], [])
        # add Outline Node
        sub_graph.add_node(
            id=input.id,
            name=outline_name,
            label="Outline",
            properties={"id": input.id, "name": outline_name},
        )

        parent_id = getattr(input, "parent_id", None)
        if parent_id is not None:
            # add Outline_childOf_Outline edge
            sub_graph.add_edge(
                s_id=input.id,
                s_label="Outline",
                p="childOf",
                o_id=parent_id,
                o_label="Outline",
                properties={},
            )

        # add Outline_sourceChunk_Chunk edge
        sub_graph.add_edge(
            s_id=input.id,
            s_label="Outline",
            p="sourceChunk",
            o_id=f"{input.id}",
            o_label=o_label,
            properties={},
        )

        return [sub_graph]
