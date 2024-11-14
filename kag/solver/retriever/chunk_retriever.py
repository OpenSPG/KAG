from typing import List

from kag.interface import KagBaseModule


class ChunkRetriever(KagBaseModule):
    """
    An abstract base class for chunk retrieval strategies.

    This class provides a template for implementing different retrieval and reranking strategies for chunks of text.

    Methods:
        recall_docs(query: str, top_k: int = 5, **kwargs) -> List[str]:
            Recalls documents based on the given query.

        rerank_docs(queries: List[str], passages: List[str]) -> List[str]:
            Reranks the retrieved passages based on the given queries.
    """

    def recall_docs(self, query: str, top_k: int = 5, **kwargs) -> List[str]:
        """
        Recalls documents based on the given query.

        Parameters:
            query (str): The query string to search for.
            top_k (int, optional): The number of top documents to return. Defaults to 5.
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
