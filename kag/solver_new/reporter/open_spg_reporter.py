import logging
from typing import List

from kag.common.conf import KAG_PROJECT_CONF

from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.logic.core_modules.common.one_hop_graph import RetrievedData, KgGraph, ChunkData
from knext.common.rest import ApiClient, Configuration
from knext.reasoner import ReasonerApi
from knext.reasoner.rest.models import TaskStreamRequest
from knext.reasoner.rest.models.ref_doc import RefDoc
from knext.reasoner.rest.models.ref_doc_set import RefDocSet
from knext.reasoner.rest.models.stream_data import StreamData

logger = logging.getLogger()

def trans_retrieved_data_to_report_data(tag_name, retrieved_data_list: List[RetrievedData]):
    report_data = []
    """
    {
        "id": "02c5ef73c6b90f85",
        "content": "于谦（1398年5月13日－1457年2月16日），字廷益，号节庵，浙江杭州府钱塘县（今杭州市上城区）人。明朝政治家、军事家、民族英雄。",
        "document_id": "53052eb0f40b11ef817442010a8a0006",
        "document_name": "test.txt"
    }"""
    for data in retrieved_data_list:
        if isinstance(data, KgGraph):
            all_spo = data.get_all_spo()
            for spo in all_spo:
                report_data.append(RefDoc(
                    id=spo.to_show_id(),
                    content=str(spo),
                    document_id=spo.to_show_id(),
                    document_name="graph data"
                ))
        elif isinstance(data, ChunkData):
            report_data.append(RefDoc(
                id=data.chunk_id,
                content=data.content,
                document_id=data.chunk_id,
                document_name=data.title
            ))
    doc_set = RefDocSet(id=tag_name, type="chunk", info=report_data)
    return doc_set


@ReporterABC.register("open_spg_reporter")
class OpenSPGReporter(ReporterABC):
    def __init__(self, task_id, **kwargs):
        super().__init__(**kwargs)
        self.task_id = task_id
        self.host = KAG_PROJECT_CONF.host_addr
        self.project_id = KAG_PROJECT_CONF.project_id
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
        self.client: ReasonerApi = ReasonerApi(
            api_client=ApiClient(configuration=Configuration(host="http://svc-8hpkrb78p78kwph9.cloudide.svc.et15-sqa.alipay.net:8080"))
        )
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
        report_data, is_finish = self.generate_report_data()
        content = StreamData(answer=report_data["content"]["answer"],
                             reference=report_data["content"]["reference"],
                             think=report_data["content"]["thinker"])
        request = TaskStreamRequest(task_id=self.task_id, content=content, status_enum="FINISH" if is_finish else "RUNNING")
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
                report_to_spg_data["content"]["reference"].append(trans_retrieved_data_to_report_data(report_data["tag_name"], content))

            status = report_data["status"]
            processed_report_record.append(report_id)
            if status != "finish":
                break
        is_finish = status == "finish" and segment_name == "answer"
        return report_to_spg_data, is_finish
    def __str__(self):
        return "\n".join([f"{line['segment']} {line['tag_name']} {line['content']} {line['status']}" for line in self.report_record.keys()])