import logging
import threading
import time
from typing import List

from kag.common.conf import KAG_PROJECT_CONF

from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_hybrid_executor import KAGRetrievedResponse
from knext.common.rest import ApiClient, Configuration
from knext.reasoner import ReasonerApi
from knext.reasoner.rest.models import TaskStreamRequest
from knext.reasoner.rest.models.metrics import Metrics
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
        self._lock = threading.Lock()
        self.task_id = task_id
        self.host = host_addr
        self.project_id = project_id
        self.report_stream_data = {}
        self.report_segment_time = {}
        self.report_record = []
        self.tag_mapping = {
            "Rewrite query": {
                "en": "## Rewriting question using LLM\n--------- \n {content}",
                "zh": "## 正在使用LLM重写问题\n--------- \n {content}"
            },
            "Final Answer": {
                "en": "## Generating final answer\n--------- \n {content}",
                "zh": "## 正在生成最终答案\n--------- \n {content}"
            },
            "Iterative planning": {
                "en": "## Iterative planning\n--------- \n {content}",
                "zh": "## 正在思考当前步骤\n--------- \n {content}"
            },
            "Static planning": {
                "en": "## Global planning\n--------- \n {content}",
                "zh": "## 正在思考全局步骤\n--------- \n {content}"
            },
            "begin_kg_retriever": {
                "en": "#### Starting KG retriever\n--------- \n Retrieving sub-question: {content}",
                "zh": "#### 正在执行知识图谱检索\n--------- \n 检索子问题为： {content}"
            },
            "end_kg_retriever": {
                "en": "#### KG retriever completed\n {content}",
                "zh": "#### 检索结果为\n {content}"
            },
            "rc_retriever_begin": {
                "en": "#### Starting chunk retriever\n--------- \n Retrieving sub-question: {content}",
                "zh": "#### 正在执行文档检索\n--------- \n 检索子问题为： {content}"
            },
            "rc_retriever_rewrite": {
                "en": "#### Rewriting chunk retriever query\n--------- \n Rewritten question:\n {content}",
                "zh": "#### 正在根据依赖问题重写检索子问题\n--------- 重写问题为：\n {content}"
            },
            "rc_retriever_end": {
                "en": "#### Chunk retriever completed, retrieved {content} documents",
                "zh": "#### 检索结束，共计检索文档 {content} 篇"
            },
            "rc_retriever_summary": {
                "en": "#### Summarizing retrieved documents\n {content}",
                "zh": "#### 正在对文档进行总结\n {content}"
            },
            "begin_kag_retriever": {
                "en": "### Starting KAG retriever\n--------- \n Retrieving question: {content}",
                "zh": "### 正在执行KAG检索\n--------- \n 检索问题为： {content}"
            },
            "logic_node": {
                "en": """#### Translate query to logic form expression
--------- 
```json
{content}
```""",
                "zh": """#### 将query转换成逻辑形式表达
--------- 
```json
{content}
```"""
            },
            "kag_retriever_result": {
                "en": "### Retrieved documents\n--------- \n {content}",
                "zh": "### 检索到的文档\n--------- \n {content}"
            },
            "end_kag_retriever": {
                "en": "### KAG retriever completed\n {content}",
                "zh": "### KAG检索结束\n {content}"
            },
            "failed_kag_retriever": {
                "en": """### KAG retriever failed
--------- 
```json
{content}
```
""",
                "zh": """KAG检索失败
--------- 
```json
{content}
```
                """
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
            "status": status,
            "time": time.time()
        }
        self.report_record.append(report_id)
        if segment not in self.report_segment_time:
            with self._lock:
                if segment not in self.report_segment_time:
                    self.report_segment_time[segment] = {
                        "start_time": time.time(),
                    }

    def do_report(self):
        if not self.client:
            return
        content, status_enum, metrics = self.generate_report_data()

        request = TaskStreamRequest(task_id=self.task_id, content=content, status_enum=status_enum, metrics=metrics)
        logging.info(f"do_report:{request}")
        return self.client.reasoner_dialog_report_completions_post(task_stream_request=request)

    def get_tag_template(self, tag_name):
        for name in self.tag_mapping:
            if name in tag_name:
                return self.tag_mapping[name][KAG_PROJECT_CONF.language]
        return None

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
        thinker_cost = 0.0
        for report_id in self.report_record:
            if report_id in processed_report_record:
                continue
            report_data = self.report_stream_data[report_id]
            segment_name = report_data["segment"]
            tag_template = self.get_tag_template(report_data["tag_name"])
            report_time = report_data["time"]
            content = report_data["content"]
            if segment_name == "thinker":
                if tag_template is None:
                    report_to_spg_data["content"][segment_name] += str(content)
                else:
                    report_to_spg_data["content"][segment_name] += tag_template.format(content=str(content))
                report_to_spg_data["content"][segment_name] += "\n\n"
                thinker_start_time = self.report_segment_time.get(segment_name, {
                    "start_time": time.time()
                })["start_time"]
                thinker_cost = report_time - thinker_start_time if report_time > thinker_start_time else 0.0

            elif segment_name == "answer":
                if not report_to_spg_data["content"]["thinker"].endswith("</think>"):
                    report_to_spg_data["content"]["thinker"] += "</think>"
                report_to_spg_data["content"][segment_name] = content
            elif segment_name == "reference":
                if isinstance(content, KAGRetrievedResponse):
                    refer_list = content.to_reference_list()
                    ref_doc_set = generate_ref_doc_set(report_data["tag_name"], "chunk", refer_list)
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
        return content, status, Metrics(thinker_cost=thinker_cost)
    def __str__(self):
        return "\n".join([f"{line['segment']} {line['tag_name']} {line['content']} {line['status']}" for line in self.report_record.keys()])