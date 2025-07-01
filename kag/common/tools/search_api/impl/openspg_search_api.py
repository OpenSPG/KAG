from typing import List

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.common.tools.search_api.search_api_abc import SearchApiABC
from knext.search.client import SearchClient


@SearchApiABC.register("openspg_search_api", as_default=True)
class OpenSPGSearchAPI(SearchApiABC):
    def __init__(self, project_id=None, host_addr=None, **kwargs):
        super().__init__(**kwargs)
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.project_id = project_id or kag_project_config.project_id
        self.host_addr = host_addr or kag_project_config.host_addr
        if self.host_addr is None or self.project_id is None:
            self.sc = None
        else:
            self.sc = SearchClient(
                host_addr=self.host_addr, project_id=int(self.project_id)
            )

    def search_text(
        self, query_string, label_constraints=None, topk=10, params=None
    ) -> List:
        if self.sc:
            return self.sc.search_text(
                query_string=query_string,
                label_constraints=label_constraints,
                topk=topk,
                params=params,
            )
        return []

    def search_vector(
        self, label, property_key, query_vector, topk=10, ef_search=None, params=None
    ) -> List:
        if self.sc is None:
            return []
        res = self.sc.search_vector(
            label=label,
            property_key=property_key,
            query_vector=query_vector,
            topk=topk,
            ef_search=ef_search,
            params=params,
        )
        if res is None:
            return []
        return res

    def search_custom(self, custom_query, params=None) -> List:
        if self.sc is None:
            return []
        return self.sc.search_custom(
            custom_query=custom_query,
            params=params,
        )
