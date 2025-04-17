from kag.builder.component import KGWriter
from typing import List

from kag.builder.component.writer.kg_writer import AlterOperationEnum

from knext.common.base.runnable import Input, Output


class EventKGWriter(KGWriter):
    def __init__(self, project_id: str = None, **kwargs):
        super().__init__(project_id, **kwargs)

    def invoke(
        self,
        input: Input,
        alter_operation: str = AlterOperationEnum.Upsert,
        lead_to_builder: bool = True,
    ) -> List[Output]:
        return super().invoke(
            input, alter_operation=alter_operation, lead_to_builder=lead_to_builder
        )
