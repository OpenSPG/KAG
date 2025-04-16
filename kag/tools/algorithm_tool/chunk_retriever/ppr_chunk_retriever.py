import logging
import time
from concurrent.futures import ThreadPoolExecutor

from typing import List, Dict, Tuple

from kag.common.conf import KAG_PROJECT_CONF, KAG_CONFIG
from kag.common.utils import get_recall_node_label
from kag.interface import ToolABC, VectorizeModelABC, LLMClient
from kag.interface.solver.model.one_hop_graph import EntityData, ChunkData, RelationData, Prop
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.text_sim_by_vector import TextSimilarity
from kag.common.config import LogicFormConfiguration
from kag.tools.graph_api.graph_api_abc import GraphApiABC
from kag.tools.search_api.search_api_abc import SearchApiABC

from kag.tools.algorithm_tool.graph_retriever.entity_linking import EntityLinking
from kag.tools.algorithm_tool.ner import Ner
from knext.schema.client import CHUNK_TYPE

logger = logging.getLogger()


@ToolABC.register("ppr_chunk_retriever")
class PprChunkRetriever(ToolABC):
    def __init__(
        self,
        llm_client: LLMClient,
        vectorize_model: VectorizeModelABC = None,
        graph_api: GraphApiABC = None,
        search_api: SearchApiABC = None,
        match_threshold: float = 0.6,
        pagerank_weight: float = 0.5,
        ner: Ner = None,
        el: EntityLinking = None,
    ):
        super().__init__()
        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
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
            KAG_CONFIG.all_config["vectorize_model"]
        )
        self.text_similarity = TextSimilarity(vectorize_model)

        self.ner = ner or Ner(llm_module=llm_client)
        self.el = el or EntityLinking(
            vectorize_model=vectorize_model,
            graph_api=graph_api,
            search_api=search_api,
            recognition_threshold=match_threshold,
            top_k=1,
            exclude_types=["Chunk"],
        )
        self.match_threshold = match_threshold
        self.pagerank_weight = pagerank_weight

    def calculate_pagerank_scores(self, start_nodes: List[EntityData], top_k):
        """
        Calculate and retrieve PageRank scores for the given starting nodes.

        Parameters:
        start_nodes (list): A list containing document fragment IDs to be used as starting nodes for the PageRank algorithm.

        Returns:
        ppr_doc_scores (dict): A dictionary containing each document fragment ID and its corresponding PageRank score.

        This method uses the PageRank algorithm in the graph store to compute scores for document fragments. If `start_nodes` is empty,
        it returns an empty dictionary. Otherwise, it attempts to retrieve PageRank scores from the graph store and converts the result
        into a dictionary format where keys are document fragment IDs and values are their respective PageRank scores. Any exceptions,
        such as failures in running `run_pagerank_igraph_chunk`, are logged.
        """
        scores = dict()
        if len(start_nodes) != 0:
            try:
                target_type = self.schema_helper.get_label_within_prefix(CHUNK_TYPE)
                start_node_set = []
                for s in start_nodes:
                    if s.type == target_type or not s.name or not s.type:
                        continue
                    start_node_set.append(
                        {
                            "id": s.biz_id,
                            "name": s.name,
                            "type": s.type,
                        }
                    )
                if len(start_node_set) == 0:
                    return scores
                scores = self.graph_api.calculate_pagerank_scores(
                    self.schema_helper.get_label_within_prefix(CHUNK_TYPE),
                    start_node_set,
                    top_k=top_k
                )
            except Exception as e:
                logger.error(
                    f"run calculate_pagerank_scores failed, info: {e}, start_nodes: {start_nodes}",
                    exc_info=True,
                )
        return scores

    def get_all_docs_by_id(self, queries: List[str], doc_ids: list, top_k: int):
        """
        Retrieve a list of documents based on their IDs.

        Parameters:
        - queries (list of str): The query string for text matching.
        - doc_ids (list): A list of document IDs to retrieve documents.
        - top_k (int): The maximum number of documents to return.

        Returns:
        - list: A list of matched documents.
        """
        matched_docs = []
        hits_docs = []

        def process_get_doc_id(doc_id):
            if isinstance(doc_id, tuple):
                doc_score = doc_id[1]
                doc_id = doc_id[0]
            else:
                doc_score = doc_ids[doc_id]
            try:
                node = self.graph_api.get_entity_prop_by_id(
                    label=self.schema_helper.get_label_within_prefix(CHUNK_TYPE),
                    biz_id=doc_id,
                )
                node_dict = dict(node.items())
                return doc_id, ChunkData(
                        content=node_dict["content"].replace("_split_0", ""),
                        title=node_dict["name"].replace("_split_0", ""),
                        chunk_id=doc_id,
                        score=doc_score,
                    )
            except Exception as e:
                logger.warning(
                    f"{doc_id} get_entity_prop_by_id failed: {e}", exc_info=True
                )

        limit_doc_ids = doc_ids[:top_k]
        doc_maps = {}
        with ThreadPoolExecutor() as executor:
            doc_res = list(executor.map(process_get_doc_id, limit_doc_ids))
            for d in doc_res:
                doc_maps[d[0]] = d[1]
        for doc_id in limit_doc_ids:
            matched_docs.append(doc_maps[doc_id[0]])
            hits_docs.append(doc_maps[doc_id[0]].chunk_id)


        query = "\n".join(queries)
        try:
            text_matched = self.search_api.search_text(
                query, [self.schema_helper.get_label_within_prefix(CHUNK_TYPE)], topk=1
            )
            if text_matched:
                for item in text_matched:
                    if item["node"]["id"] not in hits_docs:
                        if len(matched_docs) > 0:
                            matched_docs.pop()
                        else:
                            logger.warning(f"{query} matched docs is empty")
                        matched_docs.append(
                            ChunkData(
                                content=item["node"]["content"],
                                title=item["node"]["name"],
                                chunk_id=item["node"]["id"],
                                score=item["score"],
                            )
                        )
                        break
        except Exception as e:
            logger.warning(f"{query} query chunk failed: {e}", exc_info=True)
        return matched_docs

    def linking_matched_entities(self, queries: List[str], start_entities: List[EntityData], **kwargs):
        matched_entities = start_entities
        if start_entities is None:
            matched_entities = []
        ner_maps = {}
        ner_start_time = time.time()
        logger.info(f"Extracting candidate entities using NER for queries: {queries}")
        start_entity_maps = {}
        for e in matched_entities:
            e_id = f"{e.biz_id}_{e.type}"
            start_entity_maps[e_id] = e

        def process_query(ner_query):
            """Process a single query in parallel."""
            candidate_entities = self.ner.invoke(ner_query, **kwargs)
            for candidate_entity in candidate_entities:
                query_type = candidate_entity.get_entity_first_type_or_un_std()

                ner_id = f"{candidate_entity.entity_name}_{query_type}"
                if ner_id not in ner_maps:
                    ner_maps[ner_id] = {
                        "candidate": candidate_entity,
                        "query": ner_query,
                        "query_type": query_type,
                    }
            # Use ThreadPoolExecutor to parallelize NER processing

        with ThreadPoolExecutor() as executor:
            executor.map(process_query, queries)
        logger.info(
            f"NER completed in {time.time() - ner_start_time:.2f} seconds. Found {len(ner_maps)} unique entities."
        )

        logger.info(
            f"Performing entity linking (EL) for {len(ner_maps)} candidate entities."
        )

        def process_entity(k, data):
            """Process a single entity in parallel."""
            mention = data["candidate"].entity_name

            query_entity_vector = self.vectorize_model.vectorize(mention)

            top_entities = self.el.search_api.search_vector(label="Entity",
                property_key="name",
                query_vector=query_entity_vector,
                topk=1,)
            for top_entity in top_entities:
                score = top_entity["score"]
                if score > 0.7:
                    recalled_entity = EntityData()
                    recalled_entity.score = top_entity["score"]
                    recalled_entity.biz_id = top_entity["node"]["id"]
                    recalled_entity.name = top_entity["node"]["name"]
                    recalled_entity.type = get_recall_node_label(
                        top_entity["node"]["__labels__"]
                    )
                    return [recalled_entity]
            return []

        # Use ThreadPoolExecutor to parallelize EL processing
        with ThreadPoolExecutor() as executor:
            results = list(
                executor.map(
                    lambda item: process_entity(item[0], item[1]), ner_maps.items()
                )
            )

        # Flatten the results and extend matched_entities
        for result in results:
            if result:
                for r in result:
                    e_id = f"{r.biz_id}_{r.type}"
                    if e_id in start_entity_maps:
                        continue
                    start_entity_maps[e_id] = r
                    matched_entities.append(r)
        return matched_entities


    def weightd_merge(self, ppr_chunks: Dict[str, float], dpr_chunks: Dict[str, float], alpha: float = 0.5):
        def min_max_normalize(chunks):
            if len(chunks) == 0:
                return {}
            scores = chunks.values()
            max_score = max(scores)
            min_score = min(scores)
            ret_docs = {}
            for doc_id,score in chunks.items():

                score = (score - min_score) / (max_score - min_score)
                ret_docs[doc_id] = score
            return ret_docs

        ppr_chunks = min_max_normalize(ppr_chunks)
        dpr_chunks = min_max_normalize(dpr_chunks)

        merged = {}
        for doc_id, score in ppr_chunks.items():
            if doc_id in merged:
                merged_score = merged[doc_id]
                merged_score += score * alpha
                merged[doc_id] = merged_score
            else:
                merged[doc_id] = score * alpha

        for doc_id, score in dpr_chunks.items():
            if doc_id in merged:
                merged_score = merged[doc_id]
                merged_score += score * (1 - alpha)
                merged[doc_id] = merged_score
            else:
                merged[doc_id] = score * (1 - alpha)

        sorted_scores = sorted(
            merged.items(), key=lambda item: item[1], reverse=True
        )
        return sorted_scores

    def invoke(
        self, queries: List[str], start_entities: List[EntityData], top_k: int, **kwargs
    ) -> Tuple[List[ChunkData], List[RelationData]]:
        logger.info(
            f"Starting invoke method with queries: {queries}, start_entities: {start_entities}, top_k: {top_k}"
        )

        el_start_time = time.time()

        matched_entities = self.linking_matched_entities(queries=queries, start_entities=start_entities, **kwargs)

        logger.info(
            f"Entity linking completed in {time.time() - el_start_time:.2f} seconds. Found {len(matched_entities)} unique entities."
        )

        pagerank_start_time = time.time()
        if len(matched_entities):
            pagerank_res = self.calculate_pagerank_scores(matched_entities, top_k=top_k * 20)
        else:
            pagerank_res = {}
        logger.info(
            f"PageRank calculation completed in {time.time() - pagerank_start_time:.2f} seconds."
        )
        pagerank_scores = {}
        is_need_get_doc = False
        for k,v in pagerank_res.items():
            if isinstance(v, float):
                pagerank_scores[k] = v
                is_need_get_doc = True
            else:
                pagerank_scores[k] = v['score']

        sorted_scores = sorted(
            pagerank_scores.items(), key=lambda item: item[1], reverse=True
        )
        if is_need_get_doc:
            matched_docs = self.get_all_docs_by_id(queries, sorted_scores, top_k * 20)
        else:
            matched_docs = []
            for doc_id, score in sorted_scores:
                node = pagerank_res[doc_id]["node"]
                matched_docs.append(ChunkData(
                    content=node["content"].replace("_split_0", ""),
                    title=node["name"].replace("_split_0", ""),
                    chunk_id=doc_id,
                    score=score,
                ))
        return matched_docs, self._convert_relation_datas(chunk_docs=matched_docs, matched_entities=matched_entities[:top_k])

    def _convert_relation_datas(self, chunk_docs, matched_entities):
        relation_datas = []
        def chunk_to_Node(chunk):
            chunk_type = self.schema_helper.get_label_within_prefix("Chunk")
            chunk_type_zh = self.schema_helper.node_en_zh["Chunk"]
            node = EntityData(entity_id=chunk.chunk_id, name=chunk.title, node_type=chunk_type, node_type_zh=chunk_type_zh)
            node.prop = Prop.from_dict(json_dict={
                "name": chunk.title,
                "content": chunk.content
            }, label_name=chunk_type, schema=self.schema_helper)
            node.score = chunk.score
            return node
        # Mock Relation Data
        ppr_node = EntityData(entity_id="ppr_id", name="PPR compute", node_type="PPR", node_type_zh="PPR")
        for entity in matched_entities:
            rel = RelationData.from_dict(json_dict={
                "__from_id__": entity.biz_id,
                "__from_id_type__": entity.type,
                "__to_id__": ppr_node.biz_id,
                "__to_id_type__": ppr_node.type,
                "__label__": "start",
                "score": entity.score
            }, schema=self.schema_helper)
            rel.from_entity = entity
            rel.end_entity = ppr_node
            relation_datas.append(rel)
        if matched_entities:
            for chunk in chunk_docs:
                entity = chunk_to_Node(chunk)
                rel = RelationData.from_dict(json_dict={
                    "__to_id__": entity.biz_id,
                    "__to_id_type__": entity.type,
                    "__from_id__": ppr_node.biz_id,
                    "__from_id_type__": ppr_node.type,
                    "__label__": "end",
                    "score": entity.score
                }, schema=self.schema_helper)
                rel.from_entity = ppr_node
                rel.end_entity = entity
                relation_datas.append(rel)
        return relation_datas

    def schema(self):
        return {
            "name": "ppr_chunk_retriever",
            "description": "Retrieve document chunks using Personalized PageRank algorithm with knowledge graph entities",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for context retrieval",
                    },
                    "start_entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "Entity ID in knowledge graph",
                                },
                                "type": {
                                    "type": "string",
                                    "description": "Entity type category",
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Canonical entity name",
                                },
                                "score": {
                                    "type": "string",
                                    "description": "The weight of this entity",
                                },
                            },
                            "required": ["id", "name", "score"],
                        },
                        "description": "Seed entities for personalized PageRank calculation",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top-ranked chunks to return",
                        "default": 5,
                        "minimum": 1,
                    },
                },
                "required": ["query", "start_entities"],
            },
        }
