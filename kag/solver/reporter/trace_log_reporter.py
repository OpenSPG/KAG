import logging
import time

from kag.interface import RetrieverOutput
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_hybrid_executor import (
    KAGRetrievedResponse,
)
from kag.solver.reporter.open_spg_reporter import OpenSPGReporter

logger = logging.getLogger()


class TraceLog:
    def __init__(self):
        self.decompose = []
        self.thinker = {}
        self.answer = ""
        self.generator = []
        self.reference = []

    def to_dict(self):
        return {
            "decompose": self.decompose,
            "thinker": self.thinker,
            "generator": self.generator,
            "answer": self.answer,
            "reference": [ref.to_dict() for ref in self.reference],
        }


@ReporterABC.register("trace_log_reporter")
class TraceLogReporter(OpenSPGReporter):
    def __init__(self, **kwargs):
        super().__init__(0, **kwargs)

    def do_report(self):
        return self.generate_report_data()

    def generate_report_data(self):
        processed_report_record = []
        report_to_spg_data = TraceLog()
        status = ""
        segment_name = ""
        for report_id in self.report_record:
            if report_id in processed_report_record:
                continue
            report_data = self.report_stream_data[report_id]
            segment_name = report_data["segment"]
            content = report_data["content"]
            if segment_name == "thinker":
                report_to_spg_data.thinker[report_data["tag_name"]] = f"{content}"
            elif segment_name == "answer":
                report_to_spg_data.answer = content
            elif segment_name == "reference":
                if isinstance(content, KAGRetrievedResponse):
                    report_to_spg_data.decompose.append(content.to_dict())
                elif isinstance(content, RetrieverOutput):
                    report_to_spg_data.decompose.append(content.to_dict())
                else:
                    logger.warning(f"Unknown reference type {type(content)}")
                    continue
            elif segment_name == "generator":
                report_to_spg_data.generator.append(content)
            elif segment_name == "generator_reference":
                report_to_spg_data.reference = content

            status = report_data["status"]
            processed_report_record.append(report_id)
            if status != "FINISH":
                break
        if status == "FINISH":
            if segment_name != "answer":
                status = "RUNNING"
        return report_to_spg_data, status

    def __str__(self):
        return "\n".join(
            [
                f"{line['segment']} {line['tag_name']} {line['content']} {line['status']}"
                for line in self.report_record.keys()
            ]
        )
