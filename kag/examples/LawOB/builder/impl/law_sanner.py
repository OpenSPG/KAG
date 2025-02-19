import json
import os
from typing import Type, List, Dict

from knext.common.base.runnable import Input, Output

from kag.interface import ScannerABC


@ScannerABC.register("law_dataset_scanner")
class LawCorpusScanner(ScannerABC):
    """
    A class for reading HotpotQA dataset and converting it into a list of dictionaries, inheriting from `ScannerABC`.

    This class is responsible for reading HotpotQA corpus and converting it into a list of dictionaries.
    It inherits from `ScannerABC` and overrides the necessary methods to handle HotpotQA-specific operations.
    """

    @property
    def input_types(self) -> Type[Input]:
        return str

    @property
    def output_types(self) -> Type[Output]:
        return Dict

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        """
        Loads data from a HotpotQA corpus file or JSON string and returns it as a list of dictionaries.

        This method reads HotpotQA corpus data from a file or parses a JSON string and returns it as a list of dictionaries.
        If the input is a file path, it reads the file; if the input is a JSON string, it parses the string.

        Args:
            input (Input): The HotpotQA corpus file path or JSON string to load.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of dictionaries, where each dictionary represents a HotpotQA item.
        """
        outputs = []
        with open(input, "r") as f:
            law_items = json.load(f)
            for _, v in law_items.items():
                outputs.append(v)
        return outputs
