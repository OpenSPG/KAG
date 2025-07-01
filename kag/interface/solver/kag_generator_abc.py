from abc import ABC, abstractmethod

from kag.interface.solver.kag_memory_abc import KagMemoryABC
from kag.interface.solver.base import KagBaseModule


class KAGGeneratorABC(KagBaseModule, ABC):
    """
    The Generator class is an abstract base class for generating responses using a language model module.
    It initializes prompts for judging and generating responses based on the business scene and language settings.
    """

    @abstractmethod
    def generate(self, instruction, memory: KagMemoryABC) -> str:
        raise NotImplementedError("Subclasses must implement this method")
