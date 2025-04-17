from typing import List

from kag.common.conf import KAG_PROJECT_CONF
from kag.tools.search_api.search_api_abc import SearchApiABC
from knext.search.client import SearchClient


@SearchApiABC.register("openspg_search_api", as_default=True)
class OpenSPGSearchAPI(SearchApiABC):
    def __init__(self, project_id=None, host_addr=None, **kwargs):
        super().__init__(**kwargs)
        self.project_id = project_id or KAG_PROJECT_CONF.project_id
        self.host_addr = host_addr or KAG_PROJECT_CONF.host_addr
        self.sc = SearchClient(
            host_addr=self.host_addr, project_id=int(self.project_id)
        )

    def search_text(
        self, query_string, label_constraints=None, topk=10, params=None
    ) -> List:
        return self.sc.search_text(
            query_string=query_string,
            label_constraints=label_constraints,
            topk=topk,
            params=params,
        )

    def search_vector(
        self, label, property_key, query_vector, topk=10, ef_search=None, params=None
    ) -> List:
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
