from typing import List

from tenacity import stop_after_attempt, retry

from kag.common.conf import KAG_PROJECT_CONF, KAG_CONFIG
from kag.common.registry import Registrable
from kag.interface import LLMClient, PromptABC, VectorizeModelABC
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.config import LogicFormConfiguration
from kag.common.parser.logic_node_parser import (
    GetSPONode,
    ParseLogicForm,
)
from kag.common.parser.schema_std import DefaultStdSchema


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
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_client = llm_client
        self.lf_trans_prompt = lf_trans_prompt

        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
                }
            )
        )
        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            KAG_CONFIG.all_config["vectorize_model"]
        )

        self.std_schema = DefaultStdSchema(
            vectorize_model=self.vectorize_model, llm_client=llm_client
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
