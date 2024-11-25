from typing import Union

from kag.solver.logic.common.base_model import LogicNode
from kag.solver.logic.common.one_hop_graph import KgGraph
from kag.solver.logic.common.schema import Schema


class OpExecutor:
    """
    Base class for operators execution.

    Each subclass must implement the execution and judgment functions.
    """
    def __init__(self, nl_query: str, kg_graph: KgGraph, schema: Schema, debug_info: dict):
        """
        Initializes the operator executor with necessary components.

        Parameters:
            nl_query (str): Natural language query string.
            kg_graph (KgGraph): Knowledge graph object for subsequent queries and parsing.
            schema (Schema): Semantic structure definition to assist in the parsing process.
            debug_info (dict): Debug information dictionary to record debugging information during parsing.
        """
        self.kg_graph = kg_graph
        self.schema = schema
        self.nl_query = nl_query
        self.debug_info = debug_info

    def executor(self, logic_node: LogicNode, req_id: str, param: dict) -> Union[KgGraph, list]:
        """
         Executes the operation based on the given logic node.

         This method should be implemented by subclasses to define how the operation is executed.

         Parameters:
             logic_node (LogicNode): The logic node that defines the operation to execute.
             req_id (str): Request identifier.
             param (dict): Parameters needed for the execution.

         Returns:
             Union[KgGraph, list]: The result of the operation, which could be a knowledge graph or a list.
         """
        pass

    def is_this_op(self, logic_node: LogicNode) -> bool:
        """
        Determines if this executor is responsible for the given logic node.

        This method should be implemented by subclasses to specify the conditions under which
        this executor can handle the logic node.

        Parameters:
            logic_node (LogicNode): The logic node to check.

        Returns:
            bool: True if this executor can handle the logic node, False otherwise.
        """
        pass