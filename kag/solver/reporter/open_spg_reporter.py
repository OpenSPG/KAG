import logging
import re
import threading
import time

from jinja2 import Undefined, Template

from kag.common.conf import KAGConstants, KAGConfigAccessor

from kag.interface.solver.reporter_abc import ReporterABC
from kag.interface.solver.model.one_hop_graph import (
    EntityData,
    RelationData,
)
from kag.common.utils import generate_random_string
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


def extract_ids(text):
    return re.findall(r'<reference id="([^"]+)"', text)


def generate_ref_doc_set(
    tag_name, ref_type, retrieved_data_list: list, refer_ids: list
):
    refer = []
    refer_doc_maps = {}
    for d in retrieved_data_list:
        refer_doc_maps[d["id"]] = RefDoc(
            id=d["id"],
            content=d["content"],
            document_id=d["document_id"],
            document_name=d["document_name"],
            url=d.get("url", None),
        )
    if refer_ids is not None:
        for refer_id in refer_ids:
            if refer_id in refer_doc_maps:
                refer.append(refer_doc_maps[refer_id])
    else:
        for v in refer_doc_maps.values():
            refer.append(v)
    return RefDocSet(id=tag_name, type=ref_type, info=refer)


def merge_ref_doc_set(left: RefDocSet, right: RefDocSet):
    if left.type != right.type:
        return None
    left_refer = left.info
    right_refer = right.info
    left.info = list(set(left_refer + right_refer))
    return left


def _convert_spo_to_graph(graph_id, spo_retrieved_or_entities, kag_project_config):
    nodes = {}
    edges = []

    for spo_or_entity in spo_retrieved_or_entities:

        def get_label(type_en, type_zh):
            type_name = type_zh if kag_project_config.language == "zh" else type_en
            if not type_name:
                type_name = type_en
            if not type_name:
                type_name = "Entity"
            return type_name

        def _get_node(entity: EntityData):
            return DataNode(
                id=entity.to_show_id(kag_project_config.language),
                name=entity.get_short_name(),
                label=get_label(entity.type, entity.type_zh),
                properties=entity.prop.get_properties_map() if entity.prop else {},
            )

        if isinstance(spo_or_entity, RelationData):
            spo = spo_or_entity
            start_node = _get_node(spo.from_entity)
            end_node = _get_node(spo.end_entity)
            if start_node.id not in nodes:
                nodes[start_node.id] = start_node
            if end_node.id not in nodes:
                nodes[end_node.id] = end_node
            spo_id = spo.to_show_id(kag_project_config.language)
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
        elif isinstance(spo_or_entity, EntityData):
            entity = _get_node(spo_or_entity)
            if entity.id not in nodes:
                nodes[entity.id] = entity

    sub_graph = SubGraph(
        class_name=graph_id, result_nodes=list(nodes.values()), result_edges=edges
    )
    return sub_graph


class SafeDict(dict):
    def __missing__(self, key):
        return ""


def process_planning(think_str):
    result = []
    lines = think_str.split("\n")
    for l in lines:
        strip_line = l.strip()
        if strip_line == "```":
            continue

        if strip_line.lower().startswith("step"):
            result.append(f"- {strip_line}")
            continue
        if strip_line.lower().startswith("action"):
            result.append("```logical-form-chain")
            result.append(strip_line)
            result.append("```")
            continue

        result.append(strip_line)
    return "\n".join(result)


class SilentUndefined(Undefined):
    """Jinja2 undefined variable handler that suppresses errors and returns empty values."""

    def __getattr__(self, name):
        return self  # Return the undefined object itself to avoid raising an error


def render_jinja2_template(template_str, context):
    """
    Render a Jinja2 template string using the provided context dictionary.

    :param template_str: A Jinja2 template in string format.
    :param context: A dictionary containing variables used for rendering the template.
    :return: The rendered string after applying the template, or the original string if rendering fails.
    """
    try:
        template = Template(template_str, undefined=SilentUndefined)
        return template.render(**context)
    except Exception as e:
        logging.error(
            f"Jinja2 rendering failed: {e}, Original template: {template_str}"
        )
        return template_str  # Fallback to raw template string on failure


@ReporterABC.register("open_spg_reporter")
class OpenSPGReporter(ReporterABC):
    def __init__(self, task_id, host_addr=None, project_id=None, **kwargs):
        super().__init__(**kwargs)
        self.last_report = None
        self._lock = threading.Lock()
        self.task_id = task_id
        self.host = host_addr
        self.project_id = project_id
        self.report_stream_data = {}
        self.report_segment_time = {}
        self.report_record = []
        self.report_sub_segment = {}
        self.thinking_enabled = kwargs.get("thinking_enabled", True)
        self.report_all_references = kwargs.get("report_all_references", False)
        self.word_mapping = {
            "kag_merger_digest_failed": {
                "zh": "未检索到相关信息。",
                "en": "No relevant information was found.",
            },
            "kag_merger_digest": {
                "zh": """{% if chunk_num is not defined or chunk_num == 0%}
未检索到相关文档。
{% else %}
合并文档后，输出{{chunk_num}}篇文档, 检索信息结束。
{% endif %}""",
                "en": """{% if chunk_num is not defined or chunk_num == 0%}
o relevant information was found.
{% else %}
{{chunk_num}} documents were output, information retrieved end.
{% endif %}""",
            },
            "retrieved_info_digest": {
                "zh": """{% if (nodes_num is defined and nodes_num != 0) or (edges_num is defined and edges_num != 0) %}检索的子图中共有 {{ nodes_num | default(0) }} 个节点和 {{ edges_num | default(0) }} 条边。
{% endif %}
{%if chunk_num != 0 %}共检索到 {{ chunk_num }} 篇文档。
{% endif %}
{%if (chunk_num is not defined or chunk_num == 0) and ((nodes_num is not defined or nodes_num == 0) and (edges_num is not defined and edges_num == 0)) %}未检索到相关信息。
{% endif %}""",
                "en": """{% if(nodes_num is defined and nodes_num != 0) or (edges_num is defined and edges_num != 0)  %}The retrieved subgraph contains {{ nodes_num | default(0) }} nodes and {{ edges_num | default(0) }} edges.
{% endif %}
{%if chunk_num != 0 %}{{ chunk_num }} document(s) were retrieved.
{% endif %}
{%if (chunk_num is not defined or chunk_num == 0) and ((nodes_num is not defined or nodes_num == 0) and (edges_num is not defined and edges_num == 0)) %}No relevant information was found.
{% endif %}""",
            },
            "retrieved_doc_digest": {
                "zh": """{% if chunk_num is not defined or chunk_num == 0 %}
未检索到相关文档。
{% else %}
共检索到 {{ chunk_num }} 篇文档。
{% endif %}""",
                "en": """{% if chunk_num is not defined or chunk_num == 0 %}
No relevant documents were retrieved.
{% else %}
{{ chunk_num }} document(s) were retrieved.
{% endif %}""",
            },
            "next_finish": {
                "zh": "检索信息不足以回答，需要继续检索。",
                "en": "Insufficient information retrieved to answer, need to continue retrieving.",
            },
            "next_retrieved_finish": {
                "zh": """{% if edges_num is not defined or edges_num == 0 %}
        子图中无与问题相关的边，需进一步进行文档检索。
        {% else %}
        检索的子图中共有 {{ edges_num }} 条边和问题相关，还需进行chunk检索。
        {% endif %}""",
                "en": """{% if edges_num is not defined or edges_num == 0 %}
        There are no edges in the subgraph related to the question. Further document retrieval is needed.
        {% else %}
        There are {{ edges_num }} edges in the retrieved subgraph that are related to the question, and chunk retrieval is still needed.
        {% endif %}""",
            },
            "retrieved_finish": {"zh": "", "en": ""},
            "task_executing": {"en": "Executing...", "zh": "执行中..."},
            "kg_fr": {
                "en": "Open Information Extraction Graph Retrieve",
                "zh": "开放信息抽取层检索",
            },
            "kg_cs": {"en": "SPG Graph Retrieve", "zh": "SPG知识层检索"},
            "kg_rc": {"en": "RawChunk Retrieve", "zh": "文档检索"},
            "kag_merger": {
                "zh": """{% if chunk_num is not defined or chunk_num == 0 %}
未检索到相关文档。
{% else %}
重排序文档，取top {{ chunk_num }}。
{% endif %}""",
                "en": """{% if chunk_num is not defined or chunk_num == 0 %}
No relevant documents were found.
{% else %}
Rerank the documents and take the top {{ chunk_num }}.
{% endif %}""",
            },
        }
        self.tag_mapping = {
            "Graph Show": {
                "en": "{{ content }}",
                "zh": "{{ content }}",
            },
            "Rewrite query": {
                "en": "Rethinking question using LLM: {{ content }}",
                "zh": "根据依赖问题重写子问题: {{ content }}",
            },
            "language_setting": {
                "en": "",
                "zh": "这个是一个中文知识库，我们使用中文进行思考",
            },
            "Iterative planning": {
                "en": """
<step status="{{status}}" title="Global planning">

{{ content }}

{% if status == 'success' %}
</step>
{% endif %}""",
                "zh": """
<step status="{{status}}" title="思考当前步骤">

{{ content }}

{% if status == 'success' %}
</step>
{% endif %}""",
            },
            "Static planning": {
                "en": """
<step status="{{status}}" title="Global planning">

{{ content }}

{% if status == 'success' %}
</step>
{% endif %}""",
                "zh": """
<step status="{{status}}" title="思考全局步骤">

{{ content }}

{% if status == 'success' %}
</step>
{% endif %}""",
            },
            "begin_sub_kag_retriever": {
                "en": "Starting {{component_name}}: {{content}} {{desc}}",
                "zh": "执行{{component_name}}: {{content}} {{desc}}",
            },
            "end_sub_kag_retriever": {
                "en": " {{ content }}",
                "zh": " {{ content }}",
            },
            "rc_retriever_rewrite": {
                "en": """
<step status="{{status}}" title="Rewriting chunk retriever query">

Rewritten question:
{{ content }}

{% if status == 'success' %}
</step>
{% endif %}""",
                "zh": """
<step status="{{status}}" title="正在根据依赖问题重写检索子问题">

重写问题为：
{{ content }}

{% if status == 'success' %}
</step>
{% endif %}""",
            },
            "rc_retriever_summary": {
                "en": "Summarizing retrieved documents,{{ content }}",
                "zh": "对文档进行总结，{{ content }}",
            },
            "kg_retriever_summary": {
                "en": "Summarizing retrieved graph,{{ content }}",
                "zh": "对召回的知识进行总结，{{ content }}",
            },
            "retriever_summary": {
                "en": "Summarizing retrieved documents,{{ content }}",
                "zh": "对文档进行总结，{{ content }}",
            },
            "begin_summary": {
                "en": "Summarizing retrieved information, {{ content }}",
                "zh": "对检索的信息进行总结, {{ content }}",
            },
            "begin_task": {
                "en": """
<step status="{{status}}" title="Starting Task {{step}}">

{{ content }}

{% if status == 'success' %}
</step>
{% endif %}""",
                "zh": """
<step status="{{status}}" title="执行 {{step}}">

{{ content }}

{% if status == 'success' %}
</step>
{% endif %}""",
            },
            "logic_node": {
                "en": """Translate query to logic form expression


```json
{{ content }}
```""",
                "zh": """将query转换成逻辑形式表达


```json
{{ content }}
```""",
            },
            "kag_retriever_result": {
                "en": """Retrieved documents
{{ content }}""",
                "zh": """检索到的文档
{{ content }}""",
            },
            "failed_kag_retriever": {
                "en": """KAG retriever failed


```json
{{ content }}
```
""",
                "zh": """KAG检索失败


```json
{{ content }}
```
                """,
            },
            "end_math_executor": {
                "en": """Math executor completed
{{ content }}""",
                "zh": """计算结束
{{ content }}""",
            },
            "code_generator": {
                "en": """Generating code
{{ content }}

""",
                "zh": """正在生成代码
{{ content }}

""",
            },
        }
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        self.kag_project_config = kag_config.global_config

        if self.host:
            self.client: ReasonerApi = ReasonerApi(
                api_client=ApiClient(configuration=Configuration(host=self.host))
            )
        else:
            self.client = None

    def generate_content(self, report_id, tpl, datas, content_params, graph_list):
        end_word = "." if self.kag_project_config.language == "en" else "。"
        if (
            isinstance(datas, list)
            and datas
            and (isinstance(datas[0], RelationData) or isinstance(datas[0], EntityData))
        ):
            graph_id = f"graph_{generate_random_string(3)}"
            graph_list.append(
                _convert_spo_to_graph(graph_id, datas, self.kag_project_config)
            )
            tpl = self.get_tag_template("Graph Show")
            datas = f"""<graph id={graph_id}></graph>"""
        if tpl:
            format_params = {"content": datas}
            format_params.update(content_params)
            if "{" in tpl or "%}" in tpl:
                rendered = render_jinja2_template(tpl, format_params)
            else:
                rendered = tpl.format_map(SafeDict(format_params))
            datas = rendered
        elif str(datas).strip() != "":
            output = str(datas).strip()
            if output != "":

                if output[-1] != end_word:
                    output += end_word
            datas = output
        if "planning" in report_id:
            datas = process_planning(str(datas))
        return str(datas)

    def add_report_line(self, segment, tag_name, content, status, **kwargs):
        is_overwrite = kwargs.get("overwrite", True)
        report_id = tag_name
        params = {}
        for k, v in kwargs.items():
            params[k] = self.get_word_template(v, kwargs)
        report_content = content
        if isinstance(report_content, str):
            report_content = self.get_word_template(report_content, params)

        step_status = "success"
        if status not in ["FINISH", "ERROR"]:
            step_status = "loading"
        params["status"] = step_status

        if (
            is_overwrite
            or report_id not in self.report_stream_data
            or (not isinstance(report_content, str))
        ):
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

        if segment in self.report_sub_segment:
            if tag_name not in self.report_sub_segment[segment]:
                self.report_sub_segment[segment].append(tag_name)
                if parent_segment_report:
                    parent_segment_report[
                        "content"
                    ] += f"<tag_name>{report_id}</tag_name>"
        else:
            self.report_sub_segment[segment] = [tag_name]
            if parent_segment_report:
                parent_segment_report["content"] += f"<tag_name>{report_id}</tag_name>"
        with self._lock:
            self.report_record.append(report_id)
            if segment not in self.report_segment_time:

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
            if self.last_report is None:
                logger.info(f"begin do_report: {request} ret={ret}")
                self.last_report = request
            if self.last_report.to_dict() == request.to_dict():
                return
            logger.info(
                f"do_report: think={content.think} {content.answer} status={status_enum} ret={ret}"
            )
            self.last_report = request

        except Exception as e:
            logging.error(f"do_report failed:{e}")

    def get_word_template(self, word, params):
        for name in self.word_mapping:
            if not isinstance(word, str):
                continue
            if name in word:
                template = self.word_mapping[name][self.kag_project_config.language]
                if "{" in template or "%}" in template:
                    rendered = render_jinja2_template(template, params)
                else:
                    rendered = template.format_map(SafeDict(params))
                return rendered
        return word

    def get_tag_template(self, tag_name):
        for name in self.tag_mapping:
            if name in tag_name:
                return self.tag_mapping[name][self.kag_project_config.language]
        return None

    def extra_segment_report(self):
        processed_report_record = []

        think_reports = []
        answer_reports = []
        reference_reports = []

        for report_id in self.report_record:
            if report_id in processed_report_record:
                continue
            processed_report_record.append(report_id)
            report_data = self.report_stream_data[report_id]
            segment_name = report_data["segment"]
            if segment_name == "thinker":
                think_reports.append(report_data)
            elif segment_name == "answer":
                answer_reports.append(report_data)
            elif segment_name in ["reference", "generator_reference_all"]:
                reference_reports.append(report_data)
        return think_reports, answer_reports, reference_reports

    def process_think(self, think_reports, is_finished):
        think = ""
        graph_list = []
        thinker_cost = 0.0
        for report_data in think_reports:
            segment_name = report_data["segment"]
            tag_template = report_data["tag_template"]
            report_id = report_data["report_id"]
            report_time = report_data["report_time"]
            content = report_data["content"]
            kwargs = report_data.get("kwargs", {})
            status = report_data["status"]
            report_content = f"{content}"

            report_content = self.generate_content(
                report_id, tag_template, report_content, kwargs, graph_list
            )

            def generate_sub_segment_content(cur_report_id, cur_report_content):
                generated_content = cur_report_content
                sub_segments = self.report_sub_segment.get(cur_report_id, [])
                for sub_segment in sub_segments:
                    sub_segment_data = self.report_stream_data.get(sub_segment, None)
                    if not sub_segment_data:
                        continue
                    tpl = sub_segment_data["tag_template"]
                    sub_content = sub_segment_data["content"]
                    sub_kwargs = sub_segment_data.get("kwargs", {})

                    sub_segment_report = self.generate_content(
                        report_id=cur_report_id,
                        tpl=tpl,
                        datas=sub_content,
                        content_params=sub_kwargs,
                        graph_list=graph_list,
                    )
                    processed_sub_segment_content = generate_sub_segment_content(
                        sub_segment_data["report_id"], sub_segment_report
                    )
                    tag_replace_str = f"<tag_name>{sub_segment}</tag_name>"
                    generated_content = generated_content.replace(
                        tag_replace_str, processed_sub_segment_content
                    )
                return generated_content

            processed_report_content = generate_sub_segment_content(
                report_data["report_id"], report_content
            )

            think += processed_report_content + "\n\n"
            thinker_start_time = self.report_segment_time.get(
                segment_name, {"start_time": time.time()}
            )["start_time"]
            thinker_cost = (
                report_time - thinker_start_time
                if report_time > thinker_start_time
                else 0.0
            )
            if status != "FINISH":
                break
        think = f"<think>{think}"
        if is_finished:
            think += "</think>"
        return think, thinker_cost, graph_list

    def process_answer(self, answer_reports):
        answer = ""
        status = "INIT"
        for report_data in answer_reports:
            status = report_data["status"]
            report_content = f"{report_data['content']}"
            answer += report_content
        return answer, status

    def process_reference(self, reference_reports, refer_ids):
        reference = []
        for report_data in reference_reports:
            segment_name = report_data["segment"]
            content = report_data["content"]
            if segment_name == "generator_reference_all":
                ref_doc_set = generate_ref_doc_set(
                    report_data["tag_name"], "chunk", content, refer_ids
                )
                reference = [ref_doc_set]
        return reference

    def generate_report_data_pro(self):
        think_reports, answer_reports, reference_reports = self.extra_segment_report()
        answer, status = self.process_answer(answer_reports)
        think, thinker_cost, graph_list = self.process_think(
            think_reports, is_finished=status != "INIT"
        )
        refer_ids = []
        if answer:
            refer_ids = list(set(extract_ids(answer)))
        if self.report_all_references:
            refer_ids = None
        reference = self.process_reference(reference_reports, refer_ids)

        content = StreamData(
            answer=answer,
            reference=reference,
            think=think if self.thinking_enabled else "",
            subgraph=graph_list,
            metrics=Metrics(think_cost=thinker_cost),
        )
        if status != "FINISH":
            status = "RUNNING"
        return content, status, Metrics(think_cost=thinker_cost)

    def generate_report_data(self):
        return self.generate_report_data_pro()

    def __str__(self):
        return "\n".join(
            [
                f"{line['segment']} {line['tag_name']} {line['content']} {line['status']}"
                for line in self.report_record.keys()
            ]
        )
