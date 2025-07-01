from typing import List

from tenacity import stop_after_attempt, retry

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.common.registry import Registrable
from kag.common.utils import resolve_instance
from kag.interface import LLMClient, PromptABC, VectorizeModelABC
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.config import LogicFormConfiguration
from kag.common.parser.logic_node_parser import (
    GetSPONode,
    ParseLogicForm,
)
from kag.common.parser.schema_std import DefaultStdSchema
from kag.common.tools.search_api.search_api_abc import SearchApiABC


class KAGLFRewriter(Registrable):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def rewrite(self, query, **kwargs) -> List[LogicNode]:
        raise NotImplementedError()


def _process_output_query(question, sub_query: str):
    if sub_query is None:
        return question
    return sub_query


@KAGLFRewriter.register("kag_spo_lf", as_default=True)
class KAGGetSpoLF(KAGLFRewriter):
    def __init__(
        self,
        llm_client: LLMClient,
        lf_trans_prompt: PromptABC,
        vectorize_model: VectorizeModelABC = None,
        search_api: SearchApiABC = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_client = llm_client
        self.lf_trans_prompt = lf_trans_prompt
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": kag_project_config.project_id,
                    "KAG_PROJECT_HOST_ADDR": kag_project_config.host_addr,
                }
            )
        )

        self.search_api = resolve_instance(
            search_api,
            default_config={"type": "openspg_search_api"},
            from_config_func=SearchApiABC.from_config,
        )

        self.vectorize_model = resolve_instance(
            vectorize_model,
            default_config=kag_config.all_config["vectorize_model"],
            from_config_func=VectorizeModelABC.from_config,
        )

        self.std_schema = DefaultStdSchema(
            vectorize_model=self.vectorize_model, search_api=self.search_api
        )

        self.logic_node_parser = ParseLogicForm(
            schema=self.schema_helper, schema_retrieval=self.std_schema
        )

    @retry(stop=stop_after_attempt(3), reraise=True)
    def _trans_query_to_logic_form(
        self, query: str, context: str, reporter
    ) -> List[GetSPONode]:
        """Convert user query to logical form (SPO nodes)

        Args:
            query (str): User input query text
            context (str): Context for this question

        Returns:
            List[GetSPONode]: List of logical nodes representing SPO triples

        Note:
            Method is currently unimplemented and returns empty list
        """
        sub_queries, lf_nodes_str = self.llm_client.invoke(
            {"question": query, "context": context},
            self.lf_trans_prompt,
            with_json_parse=False,
            with_except=True,
            reporter=reporter,
            tag_name=f"{query}_logic_node",
            segment_name="thinker",
        )
        return self._parse_lf(
            question=query, sub_queries=sub_queries, logic_forms=lf_nodes_str
        )

    def _parse_lf(self, question, sub_queries, logic_forms) -> List[GetSPONode]:
        if sub_queries is None:
            sub_queries = []
        # process sub query
        sub_queries = [_process_output_query(question, q) for q in sub_queries]
        if len(sub_queries) != len(logic_forms):
            raise RuntimeError(
                f"sub query not equal logic form num {len(sub_queries)} != {len(logic_forms)}"
            )
        return self.logic_node_parser.parse_logic_form_set(
            logic_forms, sub_queries, question
        )

    def rewrite(self, query, **kwargs) -> List[LogicNode]:
        return self._trans_query_to_logic_form(
            query, kwargs.get("context", ""), kwargs.get("reporter", None)
        )
