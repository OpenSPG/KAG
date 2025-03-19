import json
from typing import Type, Dict, List

from kag.common.utils import processing_phrases
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
        law_name = input["name"]
        print(f"procees {law_name}")
        law_contents = input['law_content']
        """
        LegalItem-relatedChargeName->ChargeName
        LegalItem-belongToLaw->LegalName
        LegalItem-belongToItem->ItemIndex
        """
        output = []
        for i in range(len(law_contents)):
            item_name = processing_phrases(law_contents[i]["name"])
            item_content = law_contents[i]["content"]
            output.append({
                "law_name": law_name,
                "item_name": item_name,
                "item_content": item_content,
                "index": i+1,
            })
        return output
