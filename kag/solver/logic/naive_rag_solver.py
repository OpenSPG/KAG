import logging
from kag.common.registry import Registrable
from kag.interface.solver.kag_generator_abc import KAGGeneratorABC
from kag.interface.solver.kag_memory_abc import KagMemoryABC
from kag.solver.retriever.chunk_retriever import ChunkRetriever

logger = logging.getLogger(__name__)


class NaiveRagSolver(Registrable):

    def __init__(
            self,
            retriever: ChunkRetriever,
            generator: KAGGeneratorABC,
            memory: KagMemoryABC,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.retriever = retriever
        self.generator = generator
        self.memory = memory

    def run(self, question, **kwargs):
        recall_docs = self.retriever.recall_docs(queries=[question], retrieved_spo=None)
        trace_log = recall_docs
        # self.memory.save_memory(solved_answer=None, supporting_fact=recall_docs, instruction=question)
        #
        # response = self.generator.generate(instruction = question, memory = self.memory)
        return "mock answer", trace_log


