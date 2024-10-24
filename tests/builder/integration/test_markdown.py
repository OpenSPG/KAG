import logging

from kag.builder.component.extractor import KAGExtractor
from kag.builder.component.reader import MarkDownReader
from kag.builder.component.splitter import SemanticSplitter
from kag.builder.component.writer import KGWriter
from kag.solver.logic.solver_pipeline import SolverPipeline

logger = logging.getLogger(__name__)

def build():
    reader = MarkDownReader()
    splitter = SemanticSplitter()
    extractor = KAGExtractor()
    triple_writer = KGWriter()

    chain = reader >> splitter >> extractor >> triple_writer
    chain.invoke("../data/角色信息表说明.md", max_workers=16)


def ca(query):
    resp = SolverPipeline()
    answer, trace_log = resp.run(query)

    # answer = IRCoT().agent(report_log=False).solve_problem(Question(query))
    logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
    return answer


if __name__ == "__main__":
    build()
    # ca("周杰伦发行过那些专辑")
