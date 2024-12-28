from typing import List
import json

from kag.interface.retriever.chunk_retriever_abc import ChunkRetrieverABC
from kag.solver.implementation.table.search_tree import SearchTree, SearchTreeNode
from kag.common.retriever.kag_retriever import DefaultRetriever
from kag.common.llm.client import LLMClient
from kag.solver.logic.core_modules.common.one_hop_graph import (
    EntityData,
    OneHopGraphData,
    Prop,
    RelationData,
    copy_one_hop_graph_data,
)
from kag.common.base.prompt_op import PromptOp
from knext.reasoner.client import ReasonerClient
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from knext.reasoner.rest.models.reason_task_response import ReasonTaskResponse
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from knext.reasoner import ReasonTask
from kag.solver.tools.graph_api.model.table_model import TableData
from kag.solver.tools.graph_api.openspg_graph_api import (
    OpenSPGGraphApi,
    OneHopGraphData,
)


class TableRetrievalAgent(ChunkRetrieverABC):
    def __init__(self, init_question, question, **kwargs):
        super().__init__(**kwargs)
        self.init_question = init_question
        self.question = question
        self.history = SearchTree(question)
        self.chunk_retriever = DefaultRetriever(**kwargs)
        self.reason: ReasonerClient = ReasonerClient(self.host_addr, self.project_id)

        self.graph_api: OpenSPGGraphApi = OpenSPGGraphApi(
            project_id=self.project_id, host_addr=self.host_addr
        )

        self.sub_question_answer = PromptOp.load(self.biz_scene, "sub_question_answer")(
            language=self.language
        )

        self.select_docs = PromptOp.load(self.biz_scene, "select_docs")(
            language=self.language
        )
        self.gen_symbol = PromptOp.load(self.biz_scene, "retravel_gen_symbol")(
            language=self.language
        )

    def recall_docs(self, query: str, top_k: int = 5, **kwargs) -> List[str]:
        # ner_query = f"{self.init_question}；子问题：{query}"
        ner_query = query
        entities = self.chunk_retriever.named_entity_recognition(query=ner_query)
        all_entities = set()
        for entity in entities:
            all_entities.add(entity["entity"])
            for i, alias in enumerate(entity["alias"]):
                if i <= 1:
                    all_entities.add(alias)

        entities = list(all_entities)

        recall_rst = []
        kg_entities, _ = self.chunk_retriever.match_table_mertric_constraint(
            entities, top_k=10
        )

        # table recall
        if len(kg_entities) > 0:
            tables = self.chunk_retriever.retrieval_table_metric_by_vector(
                self.question, query_type="Table", top_k=1
            )
            tables = {
                table["node"]["name"]: table["node"]["content"]
                for table in tables
                if "name" in table["node"] and "content" in table["node"]
            }
            table_chunk_list = self.chunk_retriever.retrieval_table_metric_by_page_rank(
                entities=kg_entities, topk=1, target_type="Table"
            )
            table_chunk_list = {d["name"]: d["content"] for d in table_chunk_list}
            table_value_list = []
            for k, v in tables.items():
                table_value_list.append(f"# {k}\n{v}")
            for k, v in table_chunk_list.items():
                table_value_list.append(f"# {k}\n{v}")
            recall_rst.extend(table_value_list)

        # table metrics recall
        if len(kg_entities) > 0:
            table_metrics_list1 = self.chunk_retriever.retrieval_table_metric_by_vector(
                self.question, query_type="TableMetric", top_k=10
            )
            table_metrics_list1 = [node["node"] for node in table_metrics_list1]
            table_metrics_list2 = self.chunk_retriever.get_table_metrics_by_entities(
                entities=kg_entities, topk=10
            )
            table_metrics_list = table_metrics_list1 + table_metrics_list2
            table_metrics_list = [mertic["name"] for mertic in table_metrics_list]
            recall_rst.extend(table_metrics_list)

        # recall from docs
        docs_with_score = self.chunk_retriever.recall_docs(query=query, top_k=5)
        docs = ["#".join(item.split("#")[:-1]) for item in docs_with_score]
        recall_rst.extend(docs)

        return recall_rst

    def rerank_docs(self, queries: List[str], passages: List[str]) -> List[str]:
        docs = "\n\n".join(passages)
        llm: LLMClient = self.llm_module
        return llm.invoke(
            {"docs": docs, "question": self.question},
            self.select_docs,
            with_except=True,
        )

    def symbol_solver(self):
        """
        符号求解
        """

        # 根据问题，搜索20张表
        s_nodes = self.chunk_retriever._search_nodes_by_vector(
            self.question, "Table", threshold=0.5, topk=20
        )
        table_name_list = [t["node"]["name"] for t in s_nodes]

        # 生成get_spo符号
        llm: LLMClient = self.llm_module
        get_spo_list = llm.invoke(
            {"input": self.question, "table_names": ",".join(table_name_list)},
            self.gen_symbol,
            with_json_parse=False,
            with_except=True,
        )

        # 在图上查询
        graph_dict = {}
        for get_spo in get_spo_list:
            s = get_spo["s"]
            p = get_spo["p"]
            o = get_spo["o"]

            self._query_spo(s, p, o, graph_dict)
        # 返回结果

    def _query_spo(self, s, p, o, graph_dict=None):
        s_var_name = s["var"]
        s_link = s["link"]
        s_type = s["type"]

        s_id_list = []
        if s_var_name not in graph_dict:
            # 链指s
            s_nodes = self.chunk_retriever._search_nodes_by_vector(
                s_link, s_type, threshold=0.9, topk=1
            )
            if s_nodes is None or len(s_nodes) <= 0:
                return None
            s_id_list = [n["node"]["id"] for n in s_nodes]
        else:
            for node in graph_dict[s_var_name]:
                s_id_list.append(node.biz_id)

        sid_str = json.dumps(s_id_list)

        p_var_name = p["var"]
        o_var_name = o["var"]
        s_type = self._std_type(s)
        p_type = self._std_type(p)
        o_type = self._std_type(o)
        p_type = ""
        o_type = ""

        task_response: ReasonTaskResponse = self.reason.syn_execute(
            dsl_content=f"MATCH (s{s_type})-[p{p_type}]-(o{o_type}) WHERE s.id in {sid_str} RETURN s,p,o,s.id as s_id,o.id as o_id",
            start_alias="s",
        )
        task: ReasonTask = task_response.task
        if task.status != "FINISH":
            return None
        detail = task.result_table_result
        table_data = TableData.from_dict({"header": detail.header, "data": detail.rows})
        rsp_map = self.graph_api.convert_spo_to_one_graph(table=table_data)
        for _, v in rsp_map.items():
            onehop_graph: OneHopGraphData = v
            if s_var_name not in graph_dict:
                graph_dict[s_var_name] = []
            graph_dict[s_var_name].append(onehop_graph.s)
            for edge_type, edge_list in onehop_graph.in_relations.items():
                for e in edge_list:
                    e: RelationData = e
            print(onehop_graph)

    def _std_type(self, type_str):
        if isinstance(type_str, dict):
            type_str = type_str.get("type", None)
        if type_str is None or len(type_str) <= 0:
            return ""
        type_str = self.chunk_retriever.schema_util.get_label_within_prefix(type_str)
        type_str = ":" + type_str
        return type_str

    def answer(self):
        row_docs = self.recall_docs(query=self.question)
        print(f"rowdocs,query={self.question}\n{row_docs}")
        rerank_docs = self.rerank_docs(queries=[], passages=row_docs)
        print(f"rerank,query={self.question}\n{rerank_docs}")
        docs = "\n\n".join(rerank_docs)
        llm: LLMClient = self.llm_module
        answer = llm.invoke(
            {"docs": docs, "question": self.question},
            self.sub_question_answer,
            with_except=True,
        )
        if "i don't know" in answer.lower():
            # 尝试使用原始召回数据再回答一次
            docs = "\n\n".join(row_docs)
            llm: LLMClient = self.llm_module
            answer = llm.invoke(
                {"docs": docs, "question": self.question},
                self.sub_question_answer,
                with_except=True,
            )
        return answer, rerank_docs

    def get_sub_item_reall(self, entities):
        index = self.question.find("的所有子项")
        if index < 0:
            return None
        for entity in entities:
            index2 = self.question.find(entity)
            if index2 > 0 and index2 < index and len(entity) == (index - index2):
                return entity
        return None
