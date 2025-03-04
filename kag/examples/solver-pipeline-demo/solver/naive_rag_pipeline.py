from kag.interface import PipelineABC, RetrieverABC, GeneratorABC
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path


@Pipeline.register("naive_rag_pipeline")
class NaiveRAGPipeline(Pipeline):
    def __init__(
        self,
        text_retriever: RetrieverABC,
        vector_retriever: RetrieverABC,
        generator: GeneratorABC,
    ):
        self.text_retriever = text_retriever
        self.vector_retriever = vector_retriever
        self.generator = generator

    def rrf(self, rank1, rank2):
        pass

    def invoke(self, query, **kwargs):
        docs1 = self.text_retriever.invoke(query)
        docs2 = self.vector_retriever.invoke(query)
        docs = self.rrf(docs1, docs2)
        return self.generator.invoke(query, docs)


if __name__ == "__main__":
    import_modules_from_path("./src")
    pipeline_config = KAG_CONFIG.all_config["naive_rag_pipeline"]
    pipeline = PipelineABC.from_config(pipeline_config)

    query = "张学友和刘德华共同出演过哪些电影"
    result = pipeline.invoke(context)

    return result
