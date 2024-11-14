from abc import abstractmethod

from kag.interface.solver.kag_memory_abc import KagMemoryABC
from kag.interface.solver.base import KagBaseModule


class KagReflectorABC(KagBaseModule):
    def reflect_query(self, memory: KagMemoryABC, instruction: str) -> (bool, str):
        """
        Reflects on the query and determines whether it can be answered.

        :param memory (KagMemory): The context or memory information to use for rewriting.
        :param instruction (str): The original instruction to be rewritten.
        :return: A tuple (can_answer, refined_query)
            - can_answer: Whether the query can be answered (boolean)
            - refined_query: The refined query (string)
        """
        can_answer = self._can_answer(memory, instruction)
        refined_query = (
            self._refine_query(memory, instruction) if not can_answer else instruction
        )

        return can_answer, refined_query

    @abstractmethod
    def _can_answer(self, memory: KagMemoryABC, instruction: str):
        """
        Determines whether the query can be answered.

        :param memory (KagMemory): The context or memory information to use for rewriting.
        :param instruction (str): The original instruction to be rewritten.
        :return: Whether the query can be answered (boolean)
        """
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def _refine_query(self, memory: KagMemoryABC, instruction: str):
        """
        Refines the query.

        :param memory (KagMemory): The context or memory information to use for rewriting.
        :param instruction (str): The original instruction to be rewritten.
        :return: The refined query (string)
        """
        raise NotImplementedError("Subclasses must implement this method")
