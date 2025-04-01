import logging
import threading
import time

from kag.common.conf import KAG_PROJECT_CONF

from kag.interface.solver.reporter_abc import ReporterABC
from kag.interface.solver.model.one_hop_graph import (
    KgGraph,
    EntityData,
    RelationData,
)
from kag.common.utils import generate_random_string
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_hybrid_executor import (
    KAGRetrievedResponse,
)
from knext.common.rest import ApiClient, Configuration
from knext.reasoner import ReasonerApi
from knext.reasoner.rest.models import TaskStreamRequest
from knext.reasoner.rest.models.data_edge import DataEdge
from knext.reasoner.rest.models.data_node import DataNode
from knext.reasoner.rest.models.metrics import Metrics
from knext.reasoner.rest.models.ref_doc import RefDoc
from knext.reasoner.rest.models.ref_doc_set import RefDocSet
from knext.reasoner.rest.models.stream_data import StreamData
from knext.reasoner.rest.models.sub_graph import SubGraph

logger = logging.getLogger()


def generate_ref_doc_set(tag_name, ref_type, retrieved_data_list: list):
    refer = []
    for d in retrieved_data_list:
        refer.append(
            RefDoc(
                id=d["id"],
                content=d["content"],
                document_id=d["document_id"],
                document_name=d["document_name"],
            )
        )
    return RefDocSet(id=tag_name, type=ref_type, info=refer)


def merge_ref_doc_set(left: RefDocSet, right: RefDocSet):
    if left.type != right.type:
        return None
    left_refer = left.info
    right_refer = right.info
    left.info = list(set(left_refer + right_refer))
    return left


def _convert_spo_to_graph(graph_id, spo_retrieved):
    nodes = {}
    edges = []
    for spo in spo_retrieved:
        def get_label(type_en, type_zh):
            type_name = type_zh if KAG_PROJECT_CONF.language == "zh" else type_en
            if not type_name:
                type_name = type_en
            if not type_name:
                type_name = "Entity"
            return type_name

        def _get_node(entity: EntityData):
            return DataNode(
                id=entity.to_show_id(KAG_PROJECT_CONF.language),
                name=entity.get_short_name(),
                label=get_label(entity.type, entity.type_zh),
                properties=entity.prop.get_properties_map() if entity.prop else {},
            )

        start_node = _get_node(spo.from_entity)
        end_node = _get_node(spo.end_entity)
        if start_node.id not in nodes:
            nodes[start_node.id] = start_node
        if end_node.id not in nodes:
            nodes[end_node.id] = end_node
        spo_id = spo.to_show_id(KAG_PROJECT_CONF.language)
        data_spo = DataEdge(
            id=spo_id,
            _from=start_node.id,
            from_type=start_node.label,
            to=end_node.id,
            to_type=end_node.label,
            properties=spo.prop.get_properties_map() if spo.prop else {},
            label=get_label(spo.type, spo.type_zh),
        )

        edges.append(data_spo)
    sub_graph = SubGraph(
        class_name=graph_id, result_nodes=list(nodes.values()), result_edges=edges
    )
    return sub_graph


def _convert_kg_graph_to_show_graph(graph_id, kg_graph: KgGraph):
    spo_retrieved = kg_graph.get_all_spo()
    return _convert_spo_to_graph(graph_id, spo_retrieved)


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
        self.thinking_enabled = kwargs.get("thinking_enabled", True)
        self.tag_mapping = {
            "Rewrite query": {
                "en": "## Rethinking question using LLM\n--------- \n {content}",
                "zh": "## 正在使用LLM重思考问题\n--------- \n {content}",
            },
            "Final Answer": {
                "en": "## Generating final answer\n--------- \n {content}",
                "zh": "## 正在生成最终答案\n--------- \n {content}",
            },
            "Iterative planning": {
                "en": "## Iterative planning\n--------- \n {content}",
                "zh": "## 正在思考当前步骤\n--------- \n {content}",
            },
            "Static planning": {
                "en": "## Global planning\n--------- \n {content}",
                "zh": "## 正在思考全局步骤\n--------- \n {content}",
            },
            "begin_sub_kag_retriever": {
                "en": "#### Starting KG retriever\n--------- \n Retrieving sub-question: {content}",
                "zh": "#### 正在执行知识图谱检索\n--------- \n 检索子问题为： {content}",
            },
            "end_sub_kag_retriever": {
                "en": "#### KG retriever completed\n {content}",
                "zh": "#### 检索结果为\n {content}",
            },
            "rc_retriever_rewrite": {
                "en": "#### Rewriting chunk retriever query\n--------- \n Rewritten question:\n {content}",
                "zh": "#### 正在根据依赖问题重写检索子问题\n--------- 重写问题为：\n {content}",
            },
            "rc_retriever_summary": {
                "en": "#### Summarizing retrieved documents\n {content}",
                "zh": "#### 正在对文档进行总结\n {content}",
            },
            "retriever_summary": {
                "en": "#### Summarizing retrieved documents\n {content}",
                "zh": "#### 正在对文档进行总结\n {content}",
            },
            "begin_kag_retriever": {
                "en": "### Starting KAG retriever\n--------- \n Retrieving question: {content}",
                "zh": "### 正在执行KAG检索\n--------- \n 检索问题为： {content}",
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
```""",
            },
            "kag_retriever_result": {
                "en": "### Retrieved documents\n--------- \n {content}",
                "zh": "### 检索到的文档\n--------- \n {content}",
            },
            "end_kag_retriever": {
                "en": "### KAG retriever completed\n retrieved {content}",
                "zh": "### KAG检索结束\n 共计检索到 {content}",
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
                """,
            },
            "begin_math_executor": {
                "en": "### Starting math executor\n--------- \n {content}",
                "zh": "### 正在执行计算\n--------- \n {content}",
            },
            "end_math_executor": {
                "en": "### Math executor completed\n {content}",
                "zh": "### 计算结束\n {content}",
            },
            "code_generator": {
                "en": "#### Generating code\n--------- \n {content}",
                "zh": "#### 正在生成代码\n--------- \n {content}",
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
            "time": time.time(),
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

        request = TaskStreamRequest(
            task_id=self.task_id, content=content, status_enum=status_enum
        )
        # logging.info(f"do_report:{request}")
        try:
            ret = self.client.reasoner_dialog_report_completions_post(
                task_stream_request=request
            )
            logger.info(f"do_report: {request} ret={ret}")
        except Exception as e:
            logging.error(f"do_report failed:{e}")

    def get_tag_template(self, tag_name):
        for name in self.tag_mapping:
            if name in tag_name:
                return self.tag_mapping[name][KAG_PROJECT_CONF.language]
        return None

    def generate_report_data(self):
        processed_report_record = []
        report_to_spg_data = {
            "task_id": self.task_id,
            "content": {"answer": "", "reference": [], "thinker": ""},
        }
        status = ""
        segment_name = ""
        thinker_cost = 0.0
        graph_list = []
        for report_id in self.report_record:
            if report_id in processed_report_record:
                continue
            report_data = self.report_stream_data[report_id]
            segment_name = report_data["segment"]
            tag_template = self.get_tag_template(report_data["tag_name"])
            report_time = report_data["time"]
            content = report_data["content"]
            if segment_name == "thinker" and self.thinking_enabled:
                if report_to_spg_data["content"][segment_name] == "":
                    report_to_spg_data["content"][segment_name] = "<think>"
                if tag_template is None:
                    report_to_spg_data["content"][segment_name] += str(content)
                else:
                    if (
                        isinstance(content, list)
                        and content
                        and isinstance(content[0], RelationData)
                    ):
                        graph_id = f"graph_{generate_random_string(3)}"
                        graph_list.append(_convert_spo_to_graph(graph_id, content))
                        report_to_spg_data["content"][
                            segment_name
                        ] += tag_template.format(
                            content=f"""<div class={graph_id}></div>"""
                        )
                    else:
                        report_to_spg_data["content"][
                            segment_name
                        ] += tag_template.format(content=str(content))

                report_to_spg_data["content"][segment_name] += "\n\n"
                thinker_start_time = self.report_segment_time.get(
                    segment_name, {"start_time": time.time()}
                )["start_time"]
                thinker_cost = (
                    report_time - thinker_start_time
                    if report_time > thinker_start_time
                    else 0.0
                )

            elif segment_name == "answer":
                if report_to_spg_data["content"]["thinker"] and not report_to_spg_data["content"]["thinker"].endswith("</think>"):
                    report_to_spg_data["content"]["thinker"] += "</think>"
                report_to_spg_data["content"][segment_name] = content
            elif segment_name == "reference":
                if isinstance(content, KAGRetrievedResponse):
                    refer_list = content.to_reference_list()
                    ref_doc_set = generate_ref_doc_set(
                        report_data["tag_name"], "chunk", refer_list
                    )
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
            elif segment_name == "generator_reference_all":
                ref_doc_set = generate_ref_doc_set(
                    report_data["tag_name"], "chunk", content
                )
                report_to_spg_data["content"]["reference"] = [ref_doc_set]
            status = report_data["status"]
            processed_report_record.append(report_id)
            if status != "FINISH":
                break
        if status == "FINISH":
            if segment_name != "answer":
                status = "RUNNING"
        content = StreamData(
            answer=report_to_spg_data["content"]["answer"],
            reference=report_to_spg_data["content"]["reference"],
            think=report_to_spg_data["content"]["thinker"],
            subgraph=graph_list,
            metrics=Metrics(think_cost=thinker_cost),
        )
        return content, status, Metrics(think_cost=thinker_cost)

    def __str__(self):
        return "\n".join(
            [
                f"{line['segment']} {line['tag_name']} {line['content']} {line['status']}"
                for line in self.report_record.keys()
            ]
        )
