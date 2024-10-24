import logging

from kag.builder.component.extractor import KAGExtractor
from kag.builder.component.reader import PDFReader
from kag.builder.component.splitter import PatternSplitter
from kag.builder.component.writer import KGWriter
from kag.solver.logic.solver_pipeline import SolverPipeline

logger = logging.getLogger(__name__)

def build():
    reader = PDFReader()
    splitter = PatternSplitter()
    extractor = KAGExtractor()
    triple_writer = KGWriter()

    chain = reader >> splitter >> extractor >> triple_writer
    chain.invoke("tests/component/data/aiwen.pdf", max_workers=16)


def ca(query):
    resp = SolverPipeline()
    answer, trace_log = resp.run(query)

    # answer = IRCoT().agent(report_log=False).solve_problem(Question(query))
    logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
    return answer


if __name__ == "__main__":
    build()
    ca("竞业限制时间最长多久")
