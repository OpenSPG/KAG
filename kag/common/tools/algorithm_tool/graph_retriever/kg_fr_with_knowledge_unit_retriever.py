import logging
import time
from typing import List

from kag.common.config import get_default_chat_llm_config, LogicFormConfiguration
from kag.common.parser.logic_node_parser import GetSPONode
from kag.common.parser.schema_std import StdSchema
from kag.common.tools.algorithm_tool.graph_retriever.lf_kg_retriever_template import (
    KgRetrieverTemplate,
    get_std_logic_form_parser,
    std_logic_node,
)
from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
from kag.common.tools.search_api.search_api_abc import SearchApiABC
from kag.common.utils import get_recall_node_label
from kag.interface import (
    LLMClient,
    RetrieverABC,
    RetrieverOutput,
    Context,
    SchemaUtils,
    VectorizeModelABC,
    KgGraph,
    EntityData,
)

from kag.common.tools.algorithm_tool.chunk_retriever.ppr_chunk_retriever import (
    PprChunkRetriever,
)
from kag.common.tools.algorithm_tool.graph_retriever.entity_linking import EntityLinking
from kag.common.tools.algorithm_tool.graph_retriever.path_select.path_select import (
    PathSelect,
)
from kag.interface.solver.base_model import SPOBase

logger = logging.getLogger()


@RetrieverABC.register("kg_fr_knowledge_unit")
class KgFreeRetrieverWithKnowledgeUnitRetriever(RetrieverABC):
    def __init__(
        self,
        path_select: PathSelect = None,
        vectorize_model: VectorizeModelABC = None,
        entity_linking: EntityLinking = None,
        llm: LLMClient = None,
        ppr_chunk_retriever_tool: RetrieverABC = None,
        graph_api: GraphApiABC = None,
        search_api: SearchApiABC = None,
        std_schema: StdSchema = None,
        top_k=10,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm = llm or LLMClient.from_config(get_default_chat_llm_config())
        self.path_select = path_select or PathSelect.from_config(
            {"type": "fuzzy_one_hop_select"}
        )
        if isinstance(entity_linking, dict):
            entity_linking = EntityLinking.from_config(entity_linking)
        self.entity_linking = entity_linking or EntityLinking.from_config(
            {
                "type": "default_entity_linking",
                "recognition_threshold": 0.8,
                "exclude_types": ["Chunk"],
            }
        )
        self.template = KgRetrieverTemplate(
            path_select=self.path_select,
            entity_linking=self.entity_linking,
            llm_module=self.llm,
        )
        self.ppr_chunk_retriever_tool = (
            ppr_chunk_retriever_tool
            or PprChunkRetriever.from_config(
                {
                    "type": "ppr_chunk_retriever",
                    "llm_client": get_default_chat_llm_config(),
                }
            )
        )
        self.top_k = top_k
        self.std_parser = get_std_logic_form_parser(std_schema, self.kag_project_config)

        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": self.kag_project_config.project_id,
                    "KAG_PROJECT_HOST_ADDR": self.kag_project_config.host_addr,
                }
            )
        )

        self.graph_api = graph_api or GraphApiABC.from_config(
            {
                "type": "openspg_graph_api",
                "project_id": self.kag_project_config.project_id,
                "host_addr": self.kag_project_config.host_addr,
            }
        )

        self.search_api = search_api or SearchApiABC.from_config(
            {
                "type": "openspg_search_api",
                "project_id": self.kag_project_config.project_id,
                "host_addr": self.kag_project_config.host_addr,
            }
        )
        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            self.kag_config.all_config["vectorize_model"]
        )

    def get_ner(self, text):

        if ">>" in text:
            ent_list = [text.split(">>")[0].strip()]
            text = text.split(">>")[1]
        else:
            ent_list = []

        prompt = (
            "Identify 3 to 5 keywords in the following input sentence and return them. The return format should be a single string with the keywords separated by commas. \ninput:"
            + text
            + " \noutput:"
        )
        try:
            response = self.llm(prompt)
            ent_list = ent_list + response.split(",")
            ent_list = [k.strip() for k in ent_list if len(k.strip()) > 0]
        except:
            pass
        return ent_list

    def invoke(self, task, **kwargs) -> RetrieverOutput:
        start_time = time.time()
        query = task.arguments.get("rewrite_query", task.arguments["query"])
        logical_node = task.arguments.get("logic_form_node", None)
        if not logical_node:
            return RetrieverOutput(
                retriever_method=self.name,
                err_msg="No logical-form node found",
            )
        context = kwargs.get("context", Context())
        logical_node = std_logic_node(
            task_cache_id=self.kag_project_config.project_id,
            logic_node=logical_node,
            logic_parser=self.std_parser,
            context=context,
        )
        graph_data = self.template.invoke(
            query=query,
            logic_nodes=[logical_node],
            graph_data=context.variables_graph,
            is_exact_match=True,
            name=self.name,
            **kwargs,
        )

        matched_entities = []
        # selected_rel = []
        if graph_data is not None:
            s_entities = graph_data.get_entity_by_alias_without_attr(
                logical_node.s.alias_name
            )
            if s_entities:
                matched_entities.extend(s_entities)
            o_entities = graph_data.get_entity_by_alias_without_attr(
                logical_node.o.alias_name
            )
            if o_entities:
                matched_entities.extend(o_entities)
            matched_entities = list(set(matched_entities))

        def convert_search_rst_2_entity(top_entity):
            recalled_entity = EntityData()
            recalled_entity.score = top_entity["score"]
            recalled_entity.biz_id = top_entity["node"]["id"]
            recalled_entity.name = top_entity["node"]["name"]
            recalled_entity.type = get_recall_node_label(
                top_entity["node"]["__labels__"]
            )
            return recalled_entity

        if not matched_entities:
            candidate_entities = []  # self.get_ner(query)
            s_mention_name = logical_node.s.get_mention_name()
            if s_mention_name:
                candidate_entities.append(s_mention_name)
            o_mention_name = logical_node.o.get_mention_name()
            if o_mention_name:
                candidate_entities.append(o_mention_name)
            for entity in candidate_entities:
                lined_entities = self.entity_linking.invoke(
                    query=query,
                    name=entity,
                    type_name="Entity",
                    topk_k=1,
                    recognition_threshold=0.7,
                )
                if lined_entities:
                    matched_entities.extend(lined_entities)

        query_vector = self.vectorize_model.vectorize(query)

        # 1、atomic query search
        top_atmoic_query_units = self.search_api.search_vector(
            label=self.schema_helper.get_label_within_prefix("AtomicQuery"),
            property_key="name",
            query_vector=query_vector,
            topk=self.top_k,
        )

        for top_entity in top_atmoic_query_units:
            score = top_entity["score"]
            if score > 0.7:
                matched_entities.append(convert_search_rst_2_entity(top_entity))

        # 2 knowledge unit
        top_knowledge_units = self.search_api.search_vector(
            label=self.schema_helper.get_label_within_prefix("KnowledgeUnit"),
            property_key="name",
            query_vector=query_vector,
            topk=self.top_k,
        )

        for top_entity in top_knowledge_units:
            score = top_entity["score"]
            if score > 0.7:
                matched_entities.append(convert_search_rst_2_entity(top_entity))

        # recall from logical form
        if task is not None and logical_node is not None:

            triple_knowledges_units = self.recall_knowledge_unit_by_tripe(
                logical_node=logical_node, graph_data=graph_data
            )
            for triple_knowledges_unit in triple_knowledges_units:
                matched_entities.append(
                    convert_search_rst_2_entity(triple_knowledges_unit)
                )
        if matched_entities:
            output: RetrieverOutput = self.ppr_chunk_retriever_tool.invoke(
                task=task,
                start_entities=matched_entities,
                top_k=self.top_k,
            )
        else:
            output = RetrieverOutput(
                retriever_method=self.name,
                err_msg="No matched entities found",
            )

        logger.debug(
            f"{self.schema().get('name', '')} `{query}`  Retrieved chunks num: {len(output.chunks)} cost={time.time() - start_time}"
        )
        output.graphs = [graph_data]
        output.retriever_method = self.name
        return output

    def recall_knowledge_unit_by_tripe(
        self, logical_node: GetSPONode, graph_data: KgGraph
    ):
        # 拼接三元组用于检索
        def generate_entity_mention(node: SPOBase):

            mention = node.get_mention_name() if node.get_mention_name() else ""
            if mention != "":
                return [f"{node.get_un_std_entity_first_type_or_std()} {mention}"]
            s_datas: List[EntityData] = graph_data.get_entity_by_alias(node.alias_name)
            s_names = []
            if s_datas is not None:
                for s in s_datas:
                    s_names.append(s.name)
            ret = list(set(s_names))
            if len(ret):
                return ret
            return [node.get_un_std_entity_first_type_or_std()]

        s_mentions = generate_entity_mention(logical_node.s)
        o_mentions = generate_entity_mention(logical_node.o)
        p_mention = logical_node.p.get_entity_first_type_or_un_std()
        if p_mention == "Entity":
            p_mention = ""
        knowledge_unit_set = []
        for s_mention in s_mentions:
            for o_mention in o_mentions:
                triple_query = f"{s_mention} {p_mention} {o_mention}"
                rst_set = self.search_api.search_vector(
                    label=self.schema_helper.get_label_within_prefix("KnowledgeUnit"),
                    property_key="name",
                    query_vector=self.vectorize_model.vectorize(triple_query),
                    topk=self.top_k,
                )
                for r in rst_set:
                    if r["score"] < 0.7:
                        continue
                    knowledge_unit_set.append(r)
        return knowledge_unit_set

    def schema(self):
        return {
            "name": "kg_fr_retriever",
            "description": "Retrieve graph data in knowledge graph fr level",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for context retrieval",
                    },
                    "logic_form_node": {
                        "type": "object",
                        "description": "Logic node for context retrieval",
                    },
                },
                "required": ["query", "logic_form_node"],
            },
        }
