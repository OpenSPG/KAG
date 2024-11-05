import os

from kag.builder.component.vectorizer.batch_vectorizer import BatchVectorizer
from kag.builder.component import KGWriter
from kag.builder.component.reader.csv_reader import CSVReader
from kag.builder.component.extractor import SPGExtractor, KAGExtractor
from kag.builder.component.mapping.spo_mapping import SPOMapping
from kag.builder.component.splitter import LengthSplitter
from kag.builder.default_chain import (
    DefaultStructuredBuilderChain,
    DefaultUnstructuredBuilderChain,
)
from kag.common.env import init_kag_config
from knext.builder.builder_chain_abc import BuilderChainABC


class SPOBuilderChain(BuilderChainABC):
    def build(self, **kwargs):
        source = CSVReader(output_type="Dict")
        mapping = (
            SPOMapping()
            .add_field_mappings(
                s_id_col="S",
                p_type_col="P",
                o_id_col="O",
            )
            .add_sub_property_mapping("properties")
        )
        vectorizer = BatchVectorizer()
        sink = KGWriter()
        return source >> mapping >> vectorizer >> sink


class DiseaseBuilderChain(BuilderChainABC):
    def build(self, **kwargs):
        source = CSVReader(
            output_type="Chunk", id_col="idx", name_col="title", content_col="text"
        )
        splitter = LengthSplitter(split_length=2000)
        extractor = KAGExtractor()
        vectorizer = BatchVectorizer()
        sink = KGWriter()

        return source >> splitter >> extractor >> vectorizer >> sink


def import_data():
    file_path = os.path.dirname(__file__)
    init_kag_config(os.path.join(file_path, "../kag_config.cfg"))
    DefaultStructuredBuilderChain("HumanBodyPart").invoke(
        file_path=os.path.join(file_path, "data/HumanBodyPart.csv")
    )
    DefaultStructuredBuilderChain("HospitalDepartment").invoke(
        file_path=os.path.join(file_path, "data/HospitalDepartment.csv")
    )
    DiseaseBuilderChain().invoke(file_path=os.path.join(file_path, "data/Disease.csv"))

    SPOBuilderChain().invoke(file_path=os.path.join(file_path, "data/SPO.csv"))


if __name__ == "__main__":
    import_data()
