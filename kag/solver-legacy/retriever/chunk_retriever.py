from abc import ABC
from typing import List, Optional

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import KagBaseModule
from kag.interface import LLMClient
from kag.solver.logic.core_modules.common.one_hop_graph import RelationData
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.tools.graph_api.graph_api_abc import GraphApiABC
from kag.solver.tools.search_api.search_api_abc import SearchApiABC


class ChunkRetriever(KagBaseModule, ABC):
    def __init__(
        self,
        recall_num: int = 10,
        rerank_topk: int = 10,
        graph_api: GraphApiABC = None,
        search_api: SearchApiABC = None,
        llm_client: LLMClient = None,
        **kwargs
    ):
        super().__init__(llm_client, **kwargs)
        self.recall_num = recall_num
        self.rerank_topk = rerank_topk
        self.schema: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
                }
            )
        )
        self.graph_api = graph_api or GraphApiABC.from_config(
            {"type": "openspg_graph_api"}
        )

        self.search_api = search_api or SearchApiABC.from_config(
            {"type": "openspg_search_api"}
        )

    """
    An abstract base class for chunk retrieval strategies.

    This class provides a template for implementing different retrieval and reranking strategies for chunks of text.

    Methods:
        recall_docs(query: str, top_k: int = 5, retrieved_spo: Optional[List[RelationData]] = None, **kwargs) -> List[str]:
            Recalls documents based on the given query.

        rerank_docs(queries: List[str], passages: List[str]) -> List[str]:
            Reranks the retrieved passages based on the given queries.
    """

    def recall_docs(
        self,
        queries: List[str],
        retrieved_spo: Optional[List[RelationData]] = None,
        **kwargs
    ) -> List[str]:
        """
        Recalls documents based on the given query.

        Parameters:
            queries (list of str): The queries string to search for.
            retrieved_spo (Optional[List[RelationData]], optional): A list of previously retrieved relation data. Defaults to None.
            **kwargs: Additional keyword arguments for retrieval.

        Returns:
            List[str]: A list of recalled document IDs or content.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def rerank_docs(self, queries: List[str], passages: List[str]) -> List[str]:
        """
        Reranks the retrieved passages based on the given queries.

        Parameters:
            queries (List[str]): A list of query strings.
            passages (List[str]): A list of retrieved passages.

        Returns:
            List[str]: A list of reranked passage IDs or content.
        """
        raise NotImplementedError("Subclasses must implement this method")
