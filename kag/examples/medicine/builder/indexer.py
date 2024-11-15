import os
from kag.interface import (
    MappingABC,
    SourceReaderABC,
    SinkWriterABC,
    SplitterABC,
    ExtractorABC,
    VectorizerABC,
)
from kag.common.conf import KAG_CONFIG
from kag.builder.default_chain import (
    DefaultStructuredBuilderChain,
)
from kag.common.registry import Registrable, import_modules_from_path
from knext.builder.builder_chain_abc import BuilderChainABC


class SPOBuilderChain(BuilderChainABC, Registrable):
    def __init__(
        self,
        reader: SourceReaderABC,
        mapping: MappingABC,
        vectorizer: VectorizerABC,
        writer: SinkWriterABC,
    ):
        self.reader = reader
        self.mapping = mapping
        self.vectorizer = vectorizer
        self.writer = writer

    def build(self, **kwargs):

        self.mapping.add_field_mappings(
            s_id_col="S",
            p_type_col="P",
            o_id_col="O",
        ).add_sub_property_mapping("properties")

        return self.reader >> self.mapping >> self.vectorizer >> self.writer


class DiseaseBuilderChain(Registrable, BuilderChainABC):
    def __init__(
        self,
        reader: SourceReaderABC,
        splitter: SplitterABC,
        extractor: ExtractorABC,
        vectorizer: VectorizerABC,
        writer: SinkWriterABC,
    ):
        self.reader = reader
        self.splitter = splitter
        self.extractor = extractor
        self.vectorizer = vectorizer
        self.writer = writer

    def build(self, **kwargs):
        # source = CSVReader(
        #     output_type="Chunk", id_col="idx", name_col="title", content_col="text"
        # )
        # splitter = LengthSplitter(split_length=2000)
        # extractor = KAGExtractor()
        # vectorizer = BatchVectorizer()
        # sink = KGWriter()

        return (
            self.reader
            >> self.splitter
            >> self.extractor
            >> self.vectorizer
            >> self.writer
        )


def import_data():
    pwd = os.path.dirname(__file__)
    DefaultStructuredBuilderChain("HumanBodyPart").invoke(
        file_path=os.path.join(pwd, "data/HumanBodyPart.csv")
    )
    DefaultStructuredBuilderChain("HospitalDepartment").invoke(
        file_path=os.path.join(pwd, "data/HospitalDepartment.csv")
    )

    extractor_chain = DiseaseBuilderChain.from_config(
        KAG_CONFIG.all_config["extract_chain"]
    )
    extractor_chain.invoke(file_path=os.path.join(pwd, "data/Disease.csv"))

    spo_chain = SPOBuilderChain.from_config(KAG_CONFIG.all_config["spo_chain"])
    spo_chain.invoke(file_path=os.path.join(pwd, "data/SPO.csv"))


if __name__ == "__main__":
    import_modules_from_path(".")
    import_data()
