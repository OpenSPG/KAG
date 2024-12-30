import re
from typing import List
import json
import os
import copy

from kag.solver.implementation.default_reasoner import convert_lf_res_to_report_format
from kag.solver.logic.core_modules.common.utils import generate_random_string
from knext.project.client import ProjectClient
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
from kag.solver.logic.core_modules.retriver.retrieval_spo import (
    FuzzyMatchRetrievalSpo,
    ExactMatchRetrievalSpo,
)
from kag.solver.logic.core_modules.common.base_model import (
    SPOBase,
    SPOEntity,
    SPORelation,
    Identifer,
    TypeInfo,
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
from kag.common.vectorizer import Vectorizer
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity


class TableRetrievalAgent(ChunkRetrieverABC):
    def __init__(self, init_question, question, **kwargs):
        super().__init__(**kwargs)
        self.init_question = init_question
        self.question = question
        self.history = SearchTree(question)
        self.chunk_retriever = DefaultRetriever(**kwargs)
        self.reason: ReasonerClient = ReasonerClient(self.host_addr, self.project_id)

        vectorizer_config = eval(os.getenv("KAG_VECTORIZER", "{}"))
        if self.host_addr and self.project_id:
            config = ProjectClient(
                host_addr=self.host_addr, project_id=self.project_id
            ).get_config(self.project_id)
            vectorizer_config.update(config.get("vectorizer", {}))
        self.vectorizer: Vectorizer = Vectorizer.from_config(vectorizer_config)
        self.text_similarity = TextSimilarity(vec_config=vectorizer_config)
        self.fuzzy_match = FuzzyMatchRetrievalSpo(
            text_similarity=self.text_similarity, llm=self.llm_module
        )

        self.graph_api: OpenSPGGraphApi = OpenSPGGraphApi(
            project_id=self.project_id, host_addr=self.host_addr
        )

        self.sub_question_answer = PromptOp.load(self.biz_scene, "sub_question_answer")(
            language=self.language
        )

        self.select_docs = PromptOp.load(self.biz_scene, "select_docs")(
            language=self.language
        )
        self.select_graph = PromptOp.load(self.biz_scene, "select_graph")(
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
                self.question, query_type="Table", top_k=2
            )
            tables = {
                table["node"]["name"]: table["node"]["content"]
                for table in tables
                if "name" in table["node"] and "content" in table["node"]
            }
            table_chunk_list = self.chunk_retriever.retrieval_table_metric_by_page_rank(
                entities=kg_entities, topk=3, target_type="Table"
            )
            table_chunk_list = {d["name"]: d["content"] for d in table_chunk_list}
            tables.update(table_chunk_list)
            table_value_list = [f"# {k}\n{v}" for k, v in tables.items()]
            recall_rst.extend(table_value_list)

        return recall_rst

    def rerank_docs(self, queries: List[str], passages: List[str]) -> List[str]:
        if len(passages) == 0:
            return []
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
        # 根据问题，搜索10张表
        s_nodes = self.chunk_retriever._search_nodes_by_vector(
            self.question, "Table", threshold=0.5, topk=10
        )
        table_name_list = [t["node"]["name"] for t in s_nodes]
        # table_name_list = [
        #     f"表名：{t['node']['name']}\n{t['node']['content']}" for t in s_nodes
        # ]

        # 生成get_spo符号
        llm: LLMClient = self.llm_module
        get_spo_list = llm.invoke(
            {"input": self.question, "table_names": "\n".join(table_name_list)},
            self.gen_symbol,
            with_json_parse=False,
            with_except=True,
        )

        # 在图上查询
        kg_graph = KgGraph()
        for get_spo in get_spo_list:
            s = get_spo["s"]
            p = get_spo["p"]
            o = get_spo["o"]
            desc = get_spo["desc"]

            onehop_graph_list = self._query_spo(s, p, o, kg_graph)
            if onehop_graph_list is None or len(onehop_graph_list) <= 0:
                return "I don't know", None
            query = f"overall_goal: {self.question}, current_step: {desc}"
            n: GetSPONode = self._gen_get_spo_node(get_spo, query, kg_graph)
            total_one_kg_graph, matched_flag = self.fuzzy_match.match_spo(
                n=n,
                one_hop_graph_list=onehop_graph_list,
                sim_topk=20,
                disable_attr=True,
            )
            if not matched_flag:
                return "I don't know", None
            kg_graph.merge_kg_graph(total_one_kg_graph)
            kg_graph.nodes_alias.append(n.s.alias_name)
            kg_graph.nodes_alias.append(n.o.alias_name)
            kg_graph.edge_alias.append(n.p.alias_name)

        # kg_graph_deep_copy = copy.deepcopy(kg_graph)
        kg_graph_deep_copy = KgGraph()
        kg_graph_deep_copy.merge_kg_graph(kg_graph)
        self._table_kg_graph_with_desc(kg_graph_deep_copy)
        graph_docs = kg_graph_deep_copy.to_answer_path()
        graph_docs = json.dumps(graph_docs, ensure_ascii=False)

        # 回答子问题
        answer = llm.invoke(
            {"docs": graph_docs, "question": self.question},
            self.sub_question_answer,
            with_except=True,
        )

        # 转换graph为可以页面可展示的格式
        sub_logic_nodes_str = self._get_spo_list_to_str(get_spo_list)
        context = [
            "## SPO Retriever",
            "#### logic_form expression: ",
            f"```java\n{sub_logic_nodes_str}\n```",
        ]
        cur_content, sub_graph = convert_lf_res_to_report_format(
            None, f"graph_{generate_random_string(3)}", 0, [], kg_graph
        )
        context += cur_content
        history_log = {"report_info": {"context": context, "sub_graph": sub_graph}}

        return answer, [history_log]

    def _table_kg_graph_with_desc(self, kg_graph: KgGraph):
        table_cell_type = self.chunk_retriever.schema_util.get_label_within_prefix(
            "TableCell"
        )
        for _, edge_list in kg_graph.edge_map.items():
            for edge in edge_list:
                edge: RelationData = edge
                edge.from_entity.biz_id = ""
                edge.from_entity.name = edge.from_entity.get_attribute_value("raw_name")
                edge.end_entity.biz_id = ""
                edge.end_entity.name = edge.end_entity.get_attribute_value("raw_name")
                if edge.end_entity.type == table_cell_type:
                    edge.end_entity.name = edge.end_entity.get_attribute_value("desc")

    def _gen_get_spo_node(
        self, get_spo: dict, query: str, kg_graph: KgGraph
    ) -> GetSPONode:
        args = {
            "sub_query": query,
            "s": self._gen_so_base(get_spo["s"], kg_graph),
            "p": self._gen_p_base(get_spo["p"], kg_graph),
            "o": self._gen_so_base(get_spo["o"], kg_graph),
        }
        n: GetSPONode = GetSPONode(operator="", args=args)
        return n

    def _gen_p_base(self, p_obj: dict, kg_graph: KgGraph) -> SPOBase:
        alias_name = p_obj["var"]
        if "type" not in p_obj:
            _type = kg_graph.edge_map[alias_name][0].type
        else:
            _type = p_obj["type"]
        p: SPOBase = SPORelation(
            alias_name=alias_name,
            rel_type=_type,
            rel_type_zh=_type,
        )
        return p

    def _gen_so_base(self, s_obj: dict, kg_graph: KgGraph) -> SPOBase:
        alias_name = s_obj["var"]
        # _name = s_obj.get("link", None)
        _name = None
        if "type" not in s_obj:
            entity_datas = kg_graph.get_entity_by_alias(alias_name)
            if entity_datas is None:
                _type = "Entity"
            else:
                _type = entity_datas[0].type
        else:
            _type = s_obj["type"]
        s: SPOBase = SPOEntity(
            entity_id=None,
            entity_type=_type,
            entity_type_zh=_type,
            entity_name=str(_name) if _name else None,
            alias_name=alias_name,
        )
        return s

    def _get_graph_from_ids(self, id_list, graph_dict):
        valid_name_set = set(id_list)
        valid_item_set = set()
        new_graph_dict = {}
        while True:
            init_num = len(valid_item_set)
            for _, item_list in graph_dict.items():
                for item in item_list:
                    if isinstance(item, EntityData):
                        if item.name in valid_name_set:
                            valid_item_set.add(item)
                    else:
                        item: RelationData = item
                        if (
                            item.from_entity.name in valid_name_set
                            or item.end_entity.name in valid_name_set
                        ):
                            valid_item_set.add(item)
                            valid_name_set.add(item.from_entity.name)
                            valid_name_set.add(item.end_entity.name)
            after_num = len(valid_item_set)
            if init_num == after_num:
                break
        for var_name, item_list in graph_dict.items():
            new_graph_dict[var_name] = []
            for item in item_list:
                if item in valid_item_set:
                    new_graph_dict[var_name].add(item)
        return new_graph_dict

    def _graph_dict_llm_understanding(self, graph_dict: dict):
        rst_dict = {}
        for var_name, item_list in graph_dict.items():
            rst_dict[var_name] = []
            for item in item_list:
                item.prop.reomve_prop_value("csv")
                item.prop.reomve_prop_value("content")
                rst_dict[var_name].append(item.to_json())
        return json.dumps(rst_dict, ensure_ascii=False)

    def _get_spo_list_to_str(self, get_spo_list):
        get_spo_str_list = []
        for get_spo in get_spo_list:
            s = get_spo["s"]
            p = get_spo["p"]
            o = get_spo["o"]
            get_spo_str_list.append(
                f"get_spo(s={self._get_spo_str(s)},p={self._get_spo_str(p)},o={self._get_spo_str(o)})"
            )
        return "\n".join(get_spo_str_list)

    def _get_spo_str(self, s):
        the_str = f"{s['var']}"
        if "type" in s:
            the_str += f":{s['type']}"
        if "link" in s:
            link_list_str = s["link"]
            if isinstance(link_list_str, str):
                link_list_str = [link_list_str]
            the_str += f"{json.dumps(link_list_str, ensure_ascii=False)}"
        return the_str

    def _query_spo(self, s, p, o, kg_graph: KgGraph, o_with_topk=30):
        s_var_name = s["var"]

        s_id_list = []
        s_data = kg_graph.get_entity_by_alias(s_var_name)
        if s_data is None:
            s_type = s["type"]
            s_link = s["link"]
            if isinstance(s_link, str):
                s_link = [s_link]
            for link_str in s_link:
                # 链指s
                s_nodes = self.chunk_retriever._search_nodes_by_vector(
                    link_str, s_type, threshold=0.9, topk=1
                )
                if s_nodes is not None and len(s_nodes) > 0:
                    s_id_list.extend([n["node"]["id"] for n in s_nodes])
        else:
            for node in s_data:
                s_id_list.append(node.biz_id)

        sid_str = json.dumps(s_id_list)

        s_type = self._std_type(s, kg_graph)
        p_type = self._std_type(p, kg_graph)
        o_type = self._std_type(o, kg_graph)

        task_response: ReasonTaskResponse = self.reason.syn_execute(
            dsl_content=f"MATCH (s{s_type})-[p{p_type}]->(o{o_type}) WHERE s.id in {sid_str} RETURN s,p,o,s.id as s_id,o.id as o_id",
            start_alias="s",
        )
        task: ReasonTask = task_response.task
        if task.status != "FINISH":
            return None
        detail = task.result_table_result
        table_data = TableData.from_dict({"header": detail.header, "data": detail.rows})
        rsp_map = self.graph_api.convert_spo_to_one_graph(table=table_data)
        if len(rsp_map) <= 0:
            return None
        onehop_graph_list = []
        for _, v in rsp_map.items():
            onehop_graph: OneHopGraphData = v
            # new_out_relations_dict = {}
            # for edge_type, edge_list in onehop_graph.out_relations.items():
            #     o_score_and_edges = [
            #         (self._get_o_score(o, e.end_entity), e) for e in edge_list
            #     ]
            #     o_score_and_edges = sorted(
            #         o_score_and_edges, key=lambda x: x[0], reverse=True
            #     )
            #     if len(o_score_and_edges) > o_with_topk:
            #         o_score_and_edges = o_score_and_edges[:o_with_topk]
            #     if len(o_score_and_edges) > 0:
            #         new_out_relations_dict[edge_type] = [
            #             e[1] for e in o_score_and_edges
            #         ]
            # onehop_graph.out_relations = new_out_relations_dict
            if len(onehop_graph.out_relations) > 0:
                onehop_graph_list.append(onehop_graph)
        return onehop_graph_list

    def _get_o_score(self, o, o_entity: EntityData):
        if "link" not in o:
            # 不需要约束，全部返回
            return 1
        link_list = o["link"]
        if isinstance(link_list, str):
            link_list = [link_list]
        entity_str_list = [
            o_entity.prop.get_prop_value("row_name"),
            o_entity.prop.get_prop_value("col_name"),
        ]
        entity_str_list = [s for s in entity_str_list if s is not None]
        max_cosine_similarity = 0
        for link_str in link_list:
            for entity_str in entity_str_list:
                link_vector = self.chunk_retriever.vectorizer.vectorize(link_str)
                entity_vector = self.chunk_retriever.vectorizer.vectorize(entity_str)
                cosine_similarity = self.cosine_similarity(link_vector, entity_vector)
                if cosine_similarity > max_cosine_similarity:
                    max_cosine_similarity = cosine_similarity
        return max_cosine_similarity

    def cosine_similarity(self, vec1, vec2):
        import numpy as np

        dot_product = np.dot(vec1, vec2)
        norm_vec1 = np.linalg.norm(vec1)
        norm_vec2 = np.linalg.norm(vec2)
        value = dot_product / (norm_vec1 * norm_vec2)
        return value

    def _std_type(self, type_str, kg_graph: KgGraph):
        if isinstance(type_str, dict):
            tmp_type_str = type_str.get("type", None)
            if tmp_type_str is None:
                var_name = type_str["var"]
                entity_datas = kg_graph.get_entity_by_alias(var_name)
                if entity_datas is None:
                    type_str = tmp_type_str
                else:
                    type_str = next(iter(entity_datas)).type
            else:
                type_str = tmp_type_str
        if type_str is None or len(type_str) <= 0:
            return ""
        type_str = self.chunk_retriever.schema_util.get_label_within_prefix(type_str)
        type_str = ":`" + type_str + "`"
        return type_str

    def answer(self):
        row_docs = self.recall_docs(query=self.question)
        if len(row_docs) <= 0:
            return "I don't know", None
        print(f"rowdocs,query={self.question}\n{row_docs}")
        rerank_docs = self.rerank_docs(queries=[], passages=row_docs)
        if "i don't know" in rerank_docs.lower():
            return "I don't know", None
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
        return answer, [{"report_info": {"context": rerank_docs, "sub_graph": None}}]

    def get_sub_item_reall(self, entities):
        index = self.question.find("的所有子项")
        if index < 0:
            return None
        for entity in entities:
            index2 = self.question.find(entity)
            if index2 > 0 and index2 < index and len(entity) == (index - index2):
                return entity
        return None
