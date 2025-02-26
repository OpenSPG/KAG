import logging
from typing import List, Dict
from abc import ABC
from typing import List

from kag.interface import LLMClient, VectorizeModelABC
from kag.solver.retriever.path_kg_retriever import PathKgRetriever
from kag.solver.logic.core_modules.common.one_hop_graph import (
    OneHopGraphData,
    EntityData,
)
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from kag.solver.tools.graph_api.graph_api_abc import GraphApiABC
from kag.solver.tools.search_api.search_api_abc import SearchApiABC

logger = logging.getLogger()


@PathKgRetriever.register("default_path_kg_retriever", as_default=True)
class DefaultExactKgRetriever(PathKgRetriever, ABC):
    def __init__(
            self,
            el_num=5,
            llm_client: LLMClient = None,
            vectorize_model: VectorizeModelABC = None,
            graph_api: GraphApiABC = None,
            search_api: SearchApiABC = None,
            **kwargs,
    ):
        super().__init__(
            el_num, llm_client, vectorize_model, graph_api, search_api, **kwargs
        )
    def recall_multi_hop_graph(
            self,
            n: GetSPONode,
            heads: List[EntityData],
            tails: List[EntityData],
            **kwargs
    ) -> List[OneHopGraphData]:
        """
        通用多跳图召回入口
        """
        # 参数处理
        min_hops = kwargs.get('min_hops', 2)
        max_hops = kwargs.get('max_hops', 4)

        # 构建查询
        query_config = self.build_multi_hop_query(n, heads, tails, min_hops, max_hops)

        # 执行查询
        return self.execute_multi_hop_query(query_config)

    def build_multi_hop_query(
            self,
            n: GetSPONode,
            heads: List[EntityData],
            tails: List[EntityData],
            min_hops: int = 2,
            max_hops: int = 4
    ) -> Dict:
        """
        构建多跳查询参数
        """
        # 节点ID处理
        header_ids = {head.biz_id for head in heads}
        tail_ids = {tail.biz_id for tail in tails}

        # WHERE子句构造
        where_clauses = []
        params = {}
        if header_ids:
            params["source_ids"] = list(header_ids)
            where_clauses.append("s.id in $source_ids")
        if tail_ids:
            params["target_ids"] = list(tail_ids)
            where_clauses.append("o.id in $target_ids")

        # 标签生成
        source_labels = "|".join(self._generate_label(n.s, heads))
        target_labels = "|".join(self._generate_label(n.o, tails))

        return {
            "source_labels": source_labels,
            "target_labels": target_labels,
            "where": " AND ".join(where_clauses) if where_clauses else "",
            "params": params,
            "hop_range": f"*{min_hops}..{max_hops}"
        }

    def execute_multi_hop_query(
            self,
            query_params: Dict
    ) -> List[OneHopGraphData]:
        """
        执行多跳查询
        """
        cypher_template = f"""
        MATCH path=(s:{query_params['source_labels']})-[{query_params['hop_range']}]-(o:{query_params['target_labels']})
        {f"WHERE {query_params['where']}" if query_params['where'] else ""}
        UNWIND relationships(path) as p
        RETURN s, p, o, s.id as sid, o.id as oid
        """

        try:
            result = self.graph_api.execute_dsl(
                cypher_template,
                **query_params['params']
            )
            return self._parse_multi_hop_results(result)
        except Exception as e:
            logger.error(f"Multi-hop query failed: {str(e)}")
            return []

    def _parse_multi_hop_results(self, raw_data: List[Dict]) -> List[OneHopGraphData]:
        """
        解析多跳查询结果
        """
        processed = {}
        for record in raw_data:
            key = (record['sid'], record['oid'])
            if key not in processed:
                processed[key] = OneHopGraphData(
                    s=record['s'],
                    p=[record['p']],
                    o=record['o']
                )
            else:
                processed[key].p.append(record['p'])
        return list(processed.values())



