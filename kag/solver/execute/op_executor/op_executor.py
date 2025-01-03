from abc import ABC
from typing import Dict

from kag.interface import KagBaseModule
from kag.interface.solver.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils


class OpExecutor(KagBaseModule, ABC):
    """
    Base class for operators execution.

    Each subclass must implement the execution and judgment functions.
    """

    def __init__(self, schema: SchemaUtils, **kwargs):
        """
        Initializes the operator executor with necessary components.

        Parameters:

            schema (SchemaUtils): Semantic structure definition to assist in the parsing process.
        """
        super().__init__(**kwargs)
        self.schema = schema

    def executor(
        self,
        nl_query: str,
        logic_node: LogicNode,
        req_id: str,
        kg_graph: KgGraph,
        process_info: dict,
        param: dict,
    ) -> Dict:
        """
        Executes the operation based on the given logic node.

        This method should be implemented by subclasses to define how the operation is executed.

        Parameters:
            nl_query (str): Natural language query string.
            logic_node (LogicNode): The logic node that defines the operation to execute.
            req_id (str): Request identifier.
            kg_graph (KgGraph): Knowledge graph object for subsequent queries and parsing.
            process_info (dict): Processing information dictionary to record logic node result information during executing.
            param (dict): Parameters needed for the execution.

        Returns:
            Dict: The result of the operation, which could be a dict.
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
