import logging
import time
from typing import List

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.interface import VectorizeModelABC, LLMClient, PromptABC
from kag.interface.solver.model.one_hop_graph import (
    EntityData,
    RelationData,
    OneHopGraphData,
)
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.text_sim_by_vector import TextSimilarity
from kag.common.config import LogicFormConfiguration
from kag.common.parser.logic_node_parser import GetSPONode
from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
from kag.common.tools.search_api.search_api_abc import SearchApiABC
from kag.solver.utils import init_prompt_with_fallback
from kag.common.tools.algorithm_tool.graph_retriever.path_select.path_select import (
    PathSelect,
)
from kag.common.tools.algorithm_tool.graph_retriever.path_select.path_utils import (
    recall_one_hop_graph_by_entities,
)

logger = logging.getLogger()


@PathSelect.register("fuzzy_one_hop_select")
class FuzzyOneHopSelect(PathSelect):
    def __init__(
        self,
        llm_client: LLMClient,
        vectorize_model: VectorizeModelABC = None,
        graph_api: GraphApiABC = None,
        search_api: SearchApiABC = None,
        spo_retrieval_prompt: PromptABC = None,
        **kwargs,
    ):
        super().__init__()
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        self.kag_project_config = kag_config.global_config
        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": self.kag_project_config.project_id,
                    "KAG_PROJECT_HOST_ADDR": self.kag_project_config.host_addr,
                }
            )
        )
        self.graph_api = graph_api or GraphApiABC.from_config(
            {"type": "openspg_graph_api"}
        )

        self.search_api = search_api or SearchApiABC.from_config(
            {"type": "openspg_search_api"}
        )

        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            kag_config.all_config["vectorize_model"]
        )
        self.text_similarity = TextSimilarity(vectorize_model)
        self.llm_client = llm_client
        self.spo_retrieval_prompt = spo_retrieval_prompt or init_prompt_with_fallback(
            "spo_retrieval", self.kag_project_config.biz_scene
        )

    def recall_graph_data_from_knowledge_base(
        self, n: GetSPONode, heads: List[EntityData], tails: List[EntityData]
    ) -> List[OneHopGraphData]:
        return recall_one_hop_graph_by_entities(
            self.graph_api, heads=heads, tails=tails
        )

    def get_unstd_p_text(self, n: GetSPONode):
        un_std_p = n.p.get_entity_first_type_or_un_std()
        if un_std_p is None:
            logger.warning(f"get_unstd_p_text get p emtpy {n}")
            un_std_p = ""
        start_value_type = n.s.get_entity_first_type_or_un_std()
        if start_value_type is None or start_value_type == "Others":
            logger.debug(
                f"get_unstd_p_text get start_value_type {start_value_type} {n}"
            )
            start_value_type = "Entity"
        target_value_type = n.o.get_entity_first_type_or_un_std()
        if target_value_type is None or target_value_type == "Others":
            logger.debug(
                f"get_unstd_p_text get target_value_type {target_value_type} {n}"
            )
            target_value_type = "Entity"
        un_std_p = f"{start_value_type}{'[' + n.get_ele_name('s') + ']' if n.get_ele_name('s') != '' else ''} {un_std_p} {target_value_type}{'[' + n.get_ele_name('o') + ']'}"
        return un_std_p

    # def _selected_rel_by_llm(self, question, mention, candis):
    #     return self.llm_client.invoke(
    #         {"question": question, "mention": mention, "candis": candis},
    #         self.spo_retrieval_prompt,
    #         with_json_parse=True,
    #         with_except=True,
    #     )
    def _selected_rel_by_llm(self, question, mention, candis):
        try:
            response = self.llm_client.invoke(
                {"question": question, "mention": mention, "candis": candis},
                self.spo_retrieval_prompt,
                with_json_parse=True,
                with_except=True,
            )
            if not isinstance(response, list) or not all(
                isinstance(i, str) for i in response
            ):
                logger.warning("LLM returned invalid index format: %s", response)
                return []
            try:
                indices = [int(i) for i in response]
            except ValueError:
                logger.warning("LLM returned non-integer index: %s", response)
                return []

            valid_indices = [i for i in indices if 0 <= i < len(candis)]
            selected_sp = [candis[i] for i in valid_indices]

            return selected_sp
        except Exception as e:
            logger.error("Error during SPO retrieval: %s", e, exc_info=True)
            return []

    def select_relation(self, p_mention, p_candis, query=""):
        if not p_mention:
            print("p_mention is none")
            return None
        intersection = []
        res = []
        try:
            start_time = time.time()
            res = self._selected_rel_by_llm(query, p_mention, p_candis)
            logger.debug(
                f"find_best_match_p_name_by_entity_list _selected_rel_by_llm  cost={time.time() - start_time}"
            )
            for res_ in res:
                intersection.append(res_)
        except Exception as e:
            logger.warning(
                f"retrieval_spo json failed：query={query},  res={res} , except={e}",
                exc_info=True,
            )
        return [[x, 1.0] for x in intersection]

    def find_best_match_p_name_by_model(self, query: str, p: str, candi_set: dict):
        if p in candi_set:
            return [p, candi_set[p]]
        spo_retrieved = []
        sen_condi_set = []
        spo_name_map = {}
        for p_name, spo_l in candi_set.items():
            if (
                p_name.startswith("_")
                or p_name == "id"
                or p_name == "source"
                or p_name == "similar"
            ):
                continue
            for spo in spo_l:
                spo_name_map[spo] = p_name
            sen_condi_set += spo_l
        result = self.select_relation(p, sen_condi_set, query=query)
        logger.debug(
            f"retrieval_relation: p={p}, candi_set={sen_condi_set}, p_std result={result}"
        )

        if result is None or len(result) == 0:
            return spo_retrieved

        for result_ in result:
            spo = result_[0]
            try:
                spo_p_name = spo_name_map.get(spo, None)
                spo_retrieved.append([spo, spo_p_name])
            except Exception as e:
                logger.warning(
                    f"retrieval_relation: p={p}, candi_set={sen_condi_set}, p_std spo={spo}, except={e}",
                    exc_info=True,
                )
        return spo_retrieved

    def match_spo(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData]):
        # sort graph
        unstd_p_text = self.get_unstd_p_text(n)
        all_spo_text = []
        revert_value_p_map = {}
        revert_graph_map = {}
        for one_hop_graph in one_hop_graph_list:
            for k, v_set in one_hop_graph.get_s_all_relation_spo(
                len(n.p.value_list) != 0, self.kag_project_config.language
            ).items():
                for v in v_set:
                    all_spo_text.append(v)
                    revert_value_p_map[v] = k
                    revert_graph_map[v] = one_hop_graph
            for k, v_set in one_hop_graph.get_s_all_attribute_spo().items():
                for v in v_set:
                    attr_txt = f"{one_hop_graph.s.get_short_name()} {k} {v}"
                    all_spo_text.append(attr_txt)
                    revert_value_p_map[attr_txt] = k
                    revert_graph_map[attr_txt] = one_hop_graph
        start_time = time.time()
        tok5_res = self.text_similarity.text_sim_result(
            n.sub_query, all_spo_text, 15, low_score=0.3
        )
        logger.debug(
            f" _get_spo_value_in_one_hop_graph_set text similarity cost={time.time() - start_time}"
        )

        if len(tok5_res) == 0:
            return []
        candidate_name_set = {}
        for res in tok5_res:
            k = revert_value_p_map[res[0]]
            if k in candidate_name_set.keys():
                candidate_name_set[k].append(res[0])
            else:
                candidate_name_set[k] = [res[0]]
        start_time = time.time()
        spo_retrieved = self.find_best_match_p_name_by_model(
            n.sub_query, unstd_p_text, candidate_name_set
        )
        logger.debug(
            f"_get_spo_value_in_one_hop_graph_set find_best_match_p_name_by_entity_list cost={time.time() - start_time}"
        )
        result = []
        for std_spo_text, std_p in spo_retrieved:
            if std_p is None or std_p == "":
                continue
            one_hop_graph = revert_graph_map[std_spo_text]
            rel_set = one_hop_graph.get_std_p_value_by_spo_text(
                std_p,
                std_spo_text,
                len(n.p.value_list) != 0,
                self.kag_project_config.language,
            )
            result += rel_set
        return result

    def invoke(
        self,
        query,
        spo: GetSPONode,
        heads: List[EntityData],
        tails: List[EntityData],
        **kwargs,
    ) -> List[RelationData]:
        begin_time = time.time()
        one_hop_graph_list = self.recall_graph_data_from_knowledge_base(
            spo, heads, tails
        )
        start_time = time.time()
        selected_rels = self.match_spo(spo, one_hop_graph_list)
        logger.info(
            f"_fuzzy_match_spo total cost={time.time() - begin_time} cost={time.time() - start_time} selected_rels={len(selected_rels)}"
        )
        return selected_rels
