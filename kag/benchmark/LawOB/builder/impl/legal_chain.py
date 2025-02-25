import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from kag.interface import (
    ReaderABC,
    MappingABC,
    ExtractorABC,
    SplitterABC,
    VectorizerABC,
    PostProcessorABC,
    SinkWriterABC,
    KAGBuilderChain,
)
from kag.common.utils import generate_hash_id

logger = logging.getLogger(__name__)
@KAGBuilderChain.register("law_builder_chain")
class LegalStructuredBuilderChain(KAGBuilderChain):
    """
    A class representing a default SPG builder chain, used to import structured data based on schema definitions.
    It consists of a mapping component, a writer component, and an optional vectorizer component.
    """

    def __init__(
        self,
        reader: ReaderABC,
        extractor: ExtractorABC,
        writer: SinkWriterABC,
        vectorizer: VectorizerABC = None,
    ):
        """
        Initializes the DefaultStructuredBuilderChain instance.

        Args:
            mapping (MappingABC): The mapping component to be used.
            writer (SinkWriterABC): The writer component to be used.
            vectorizer (VectorizerABC, optional): The vectorizer component to be used. Defaults to None.
        """
        self.reader = reader
        self.extractor = extractor
        self.writer = writer
        self.vectorizer = vectorizer

    def build(self, **kwargs):
        """
        Construct the builder chain by connecting the mapping, vectorizer (if available), and writer components.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            KAGBuilderChain: The constructed builder chain.
        """
        if self.vectorizer:
            chain = self.reader >> self.extractor >> self.vectorizer >> self.writer
        else:
            chain = self.reader >> self.extractor >> self.vectorizer  >> self.writer

        return chain