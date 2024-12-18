from typing import List

from kag.solver.tools.search_api.search_api_abc import SearchApiABC
from knext.search.client import SearchClient


@SearchApiABC.register("openspg", as_default=True)
class OpenSPGSearchAPI(SearchApiABC):
    def __init__(self, project_id: str, host_addr: str, **kwargs):
        super().__init__(**kwargs)
        self.project_id = project_id
        self.host_addr = host_addr
        self.sc = SearchClient(host_addr=host_addr, project_id=int(project_id))

    def search_text(self, query_string, label_constraints=None, topk=10, params=None) -> List:
        return self.sc.search_text(query_string=query_string, label_constraints=label_constraints, topk=topk,
                                   params=params)

    def search_vector(
            self, label, property_key, query_vector, topk=10, ef_search=None, params=None
    ) -> List:
        return self.sc.search_vector(label=label, property_key=property_key, query_vector=query_vector, topk=topk,
                                     ef_search=ef_search, params=params)


if __name__ == "__main__":
    search_api = OpenSPGSearchAPI(project_id="4", host_addr="http://127.0.0.1:8887")
    res = search_api.search_text("test")
    assert len(res) > 0