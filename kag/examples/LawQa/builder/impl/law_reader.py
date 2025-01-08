import json
from typing import Type, Dict, List

from knext.common.base.runnable import Input, Output

from kag.interface import ReaderABC


@ReaderABC.register("law_reader")
class LawLoader(ReaderABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def input_types(self) -> Type[Input]:
        return str

    @property
    def output_types(self) -> Type[Output]:
        return Dict[str, str]

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Reads a CSV file and converts the data format based on the output type.

        Args:
            input (Input): Input parameter, expected to be a string representing the path to the CSV file.
            **kwargs: Additional keyword arguments, which may include `id_column`, `name_column`, `content_column`, etc.

        Returns:
            List[Output]:
                - If `output_types` is `Chunk`, returns a list of Chunk objects.
                - If `output_types` is `Dict`, returns a list of dictionaries.
        """
        return [input]
