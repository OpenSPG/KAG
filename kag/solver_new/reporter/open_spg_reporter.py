import logging
from typing import List

from kag.common.conf import KAG_PROJECT_CONF

from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_hybrid_executor import KAGRetrievedResponse
from knext.common.rest import ApiClient, Configuration
from knext.reasoner import ReasonerApi
from knext.reasoner.rest.models import TaskStreamRequest
from knext.reasoner.rest.models.ref_doc import RefDoc
from knext.reasoner.rest.models.ref_doc_set import RefDocSet
from knext.reasoner.rest.models.stream_data import StreamData

logger = logging.getLogger()

def generate_ref_doc_set(tag_name, ref_type, retrieved_data_list: list):
    refer = []
    for d in retrieved_data_list:
        refer.append(RefDoc(
            id=d["id"],
            content=d["content"],
            document_id=d["document_id"],
            document_name=d["document_name"]
        ))
    return RefDocSet(id=tag_name, type=ref_type, info=refer)

def merge_ref_doc_set(left:RefDocSet, right:RefDocSet):
    if left.type != right.type:
        return None
    left_refer = left.info
    right_refer = right.info
    left.info = list(set(left_refer + right_refer))
    return left


@ReporterABC.register("open_spg_reporter")
class OpenSPGReporter(ReporterABC):
    def __init__(self, task_id, host_addr=None, project_id=None, **kwargs):
        super().__init__(**kwargs)
        self.task_id = task_id
        self.host = host_addr
        self.project_id = project_id
        self.report_stream_data = {}
        self.report_record = []
        self.tag_mapping = {
            "Rewrite query": {
                "en": "rewrite question by llm",
                "zh": "正在重写问题"
            },
            "Final Answer": {
                "en": "generate answer",
                "zh": "正在生成答案"
            },
            "Iterative planning": {
                "en": "iterative planning",
                "zh": "正在思考当前步骤"
            },
            "Static planning": {
                "en": "global planning",
                "zh": "正在思考全局步骤"
            }
        }
        if self.host:
            self.client: ReasonerApi = ReasonerApi(
                api_client=ApiClient(configuration=Configuration(host=self.host))
            )
        else:
            self.client = None
    def add_report_line(self, segment, tag_name, content, status):
        report_id = f"{segment}_{tag_name}"
        self.report_stream_data[report_id] = {
            "segment": segment,
            "tag_name": tag_name,
            "content": content,
            "status": status
        }
        self.report_record.append(report_id)

    def do_report(self):
        if not self.client:
            return
        content, status_enum = self.generate_report_data()

        request = TaskStreamRequest(task_id=self.task_id, content=content, status_enum=status_enum)
        logging.info(f"do_report:{request}")
        return self.client.reasoner_dialog_report_completions_post(task_stream_request=request)

    def get_tag_name(self, tag_name):
        if tag_name in self.tag_mapping:
            return self.tag_mapping[tag_name][KAG_PROJECT_CONF.language]
        else:
            return tag_name

    def generate_report_data(self):
        processed_report_record = []
        report_to_spg_data = {
            "task_id": self.task_id,
            "content": {
                "answer": "",
                "reference": [],
                "thinker": "<think>"
            },
        }
        status = ""
        segment_name = ""
        for report_id in self.report_record:
            if report_id in processed_report_record:
                continue
            report_data = self.report_stream_data[report_id]
            segment_name = report_data["segment"]
            tag_name = self.get_tag_name(report_data["tag_name"])
            content = report_data["content"]
            if segment_name == "thinker":
                report_to_spg_data["content"][segment_name] += f"""

# {tag_name}  
--------- 
{content}  

"""
            elif segment_name == "answer":
                if not report_to_spg_data["content"]["thinker"].endswith("</think>"):
                    report_to_spg_data["content"]["thinker"] += "</think>"
                report_to_spg_data["content"][segment_name] = content
            elif segment_name == "reference":
                if isinstance(content, KAGRetrievedResponse):
                    refer_list = content.to_reference_list()
                    ref_doc_set = generate_ref_doc_set(tag_name, "chunk", refer_list)
                    for ref in report_to_spg_data["content"]["reference"]:
                        merged_data = merge_ref_doc_set(ref, ref_doc_set)
                        if merged_data:
                            ref.info = merged_data.info
                            break
                    else:
                        report_to_spg_data["content"]["reference"].append(ref_doc_set)
                else:
                    logger.warning(f"Unknown reference type {type(content)}")
                    continue
            status = report_data["status"]
            processed_report_record.append(report_id)
            if status != "FINISH":
                break
        if status == "FINISH":
            if segment_name != "answer":
                status = "RUNNING"
        content = StreamData(answer=report_to_spg_data["content"]["answer"],
                             reference=report_to_spg_data["content"]["reference"],
                             think=report_to_spg_data["content"]["thinker"])
        return content, status
    def __str__(self):
        return "\n".join([f"{line['segment']} {line['tag_name']} {line['content']} {line['status']}" for line in self.report_record.keys()])