import logging
import time

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
            "answer": self.answer,
            "generator": self.generator,
            "reference": [ref.to_dict() for ref in self.reference],
        }


@ReporterABC.register("trace_log_reporter")
class TraceLogReporter(OpenSPGReporter):
    def __init__(self, **kwargs):
        super().__init__(0, **kwargs)

    def do_report(self):
        return self.generate_report_data()

    def add_report_line(self, segment, tag_name, content, status, **kwargs):
        is_overwrite = kwargs.get("overwrite", True)
        report_id = tag_name
        params = kwargs
        report_content = content

        step_status = "success"
        if status not in ["FINISH", "ERROR"]:
            step_status = "loading"
        params["status"] = step_status


        if is_overwrite or report_id not in self.report_stream_data or (not isinstance(report_content, str)):
            tag_template = self.get_tag_template(tag_name)
            self.report_stream_data[report_id] = {
            "segment": segment,
            "report_id": report_id,
            "content": report_content,
            "report_time": time.time(),
            "kwargs": params,
            "tag_template": tag_template,
            "tag_name": tag_name,
            "time": time.time(),
            "status": status,
        }
        else:
            self.report_stream_data[report_id]["status"] = status
            self.report_stream_data[report_id]["kwargs"] = params
            self.report_stream_data[report_id]["time"] = time.time()
            self.report_stream_data[report_id]["content"] += f"{report_content}"

        parent_segment_report = self.report_stream_data.get(segment, None)

        if isinstance(self.report_stream_data[report_id]["content"], str):
            if segment in self.report_sub_segment:
                if tag_name not in self.report_sub_segment[segment]:
                    self.report_sub_segment[segment].append(tag_name)
                    if parent_segment_report:
                        parent_segment_report["content"] += self.report_stream_data[report_id]["content"] +"\r\n"
            else:
                self.report_sub_segment[segment] = [tag_name]
                if parent_segment_report:
                    parent_segment_report["content"] += self.report_stream_data[report_id]["content"] +"\r\n"
        with self._lock:
            self.report_record.append(report_id)
            if segment not in self.report_segment_time:

                if segment not in self.report_segment_time:
                    self.report_segment_time[segment] = {
                        "start_time": time.time(),
                    }


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
