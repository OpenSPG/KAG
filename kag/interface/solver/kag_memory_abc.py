from abc import ABC, abstractmethod

from kag.interface.solver.base import KagBaseModule


class KagMemoryABC(KagBaseModule, ABC):
    @abstractmethod
    def save_memory(self, solved_answer, supporting_fact, instruction):
        """
        Saves the solved answer, supporting facts, and instruction.

        :param solved_answer: The solved answer.
        :param supporting_fact: The supporting fact.
        :param instruction: The instruction.
        """
        pass

    @abstractmethod
    def get_solved_answer(self) -> str:
        """
        Retrieves the solved answer.

        :return: The solved answer.
        """

    @abstractmethod
    def serialize_memory(self) -> str:
        """
        Serializes the memory to str.

        :return: Serialized memory data with str format.
        """

    @abstractmethod
    def refresh(self):
        """
        Refreshes the memory.

        This method is used to reset the memory state.
        """
