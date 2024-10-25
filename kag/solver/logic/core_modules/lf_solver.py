import json
import logging
import os
import time
from typing import List

from kag.common.vectorizer import Vectorizer
from kag.interface.retriever.chunk_retriever_abc import ChunkRetrieverABC
from kag.interface.retriever.kg_retriever_abc import KGRetrieverABC
from kag.solver.logic.core_modules.common.base_model import LFPlanResult
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.core_modules.common.utils import generate_random_string
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.logic.core_modules.lf_executor import LogicExecutor
from kag.solver.logic.core_modules.lf_generator import LFGenerator
from kag.solver.logic.core_modules.retriver.entity_linker import DefaultEntityLinker
from kag.solver.logic.core_modules.retriver.graph_retriver.dsl_executor import DslRunnerOnGraphStore
from kag.solver.logic.core_modules.retriver.schema_std import SchemaRetrieval
from knext.project.client import ProjectClient

logger = logging.getLogger()


class LFSolver:
    """
    Solver class that integrates various components to solve queries using logic forms.
    This class can't be extended to implement custom solver strategies.
    """

    def __init__(self, kg_retriever: KGRetrieverABC = None,
                 chunk_retriever: ChunkRetrieverABC = None,
                 report_tool=None, **kwargs):
        """
        Initializes the solver with necessary modules and configurations.

        Parameters:
        chunk_retriever (ChunkRetriever): An instance for chunk-level retrieval. If not provided, we will not execute chunk retrieval.
        kg_retriever (KGRetrieval): An instance for graph-level retrieval. If not provided, we will not execute retrieval on graph.
        report_tool (Tool, optional): An instance of the reporting tool. Defaults to None.

        Returns:
        None

        Raises:
        ValueError: If both `kg_retriever` and `chunk_retriever` are None.
        """
        if kg_retriever is None and chunk_retriever is None:
            raise ValueError("At least one of `kg_retriever` or `chunk_retriever` must be provided.")

        self.kg_retriever = kg_retriever
        self.chunk_retriever = chunk_retriever
        self.project_id = kwargs.get("KAG_PROJECT_ID") or os.getenv("KAG_PROJECT_ID")
        self.host_addr = kwargs.get("KAG_PROJECT_HOST_ADDR") or os.getenv("KAG_PROJECT_HOST_ADDR")
        if report_tool and report_tool.project_id:
            self.project_id = report_tool.project_id

        self.schema = SchemaUtils(LogicFormConfiguration(kwargs))
        self.schema.get_schema()
        self.std_schema = SchemaRetrieval(**kwargs)
        self.el = DefaultEntityLinker(None, self.kg_retriever)
        self.generator = LFGenerator(**kwargs)
        self.report_tool = report_tool
        self.last_iter_docs = []

        vectorizer_config = eval(os.getenv("KAG_VECTORIZER", "{}"))
        if self.host_addr and self.project_id:
            config = ProjectClient(host_addr=self.host_addr, project_id=self.project_id).get_config(self.project_id)
            vectorizer_config.update(config.get("vectorizer", {}))
        self.vectorizer: Vectorizer = Vectorizer.from_config(vectorizer_config)
        self.text_similarity = TextSimilarity(vec_config=vectorizer_config)

    def _process_history(self, history):
        """
        Processes the history to extract sub-query-answer pairs and document sets.

        Parameters:
        history (list): A list of historical query-answer pairs.

        Returns:
        tuple: A tuple containing the list of sub-query-answer pairs and the list of document sets.
        """
        sub_qa_pair = []
        docs_set = []
        for i, h in enumerate(history):
            if "sub_query" not in h:
                continue
            if 'sub_answer' in h and h['sub_answer'].lower() != "i don't know":
                sub_qa_pair.append(f"query{i + 1}: {h['sub_query']}\nanswer{i + 1}: {h['sub_answer']}")
            if "docs" in h and len(h['docs']) > 0:
                docs_set.append(h['docs'])
        return sub_qa_pair, docs_set

    def _flat_passages_set(self, passages_set: list):
        """
        Flattens the passages set and scores each passage based on its position.

        Parameters:
        passages_set (list): A list of passage sets.

        Returns:
        list: A list of passages sorted by their scores.
        """
        score_map = {}
        if len(self.last_iter_docs) > 0:
            passages_set.append(self.last_iter_docs)
        for passages in passages_set:
            passages = ["#".join(item.split("#")[:-1]) for item in passages]
            for i, passage in enumerate(passages):
                score = 1.0 / (1 + i)
                if passage in score_map:
                    score_map[passage] += score
                else:
                    score_map[passage] = score

        return [k for k, v in sorted(score_map.items(), key=lambda item: item[1], reverse=True)]

    def solve(self, query, lf_nodes: List[LFPlanResult]):
        """
        Solves the query using logic forms and returns the results.

        Parameters:
        query (str): The main query to solve.
        lf_nodes (list): A list of LFPlanResult to be solved.

        Returns:
        tuple: A tuple containing the final answer, sub-query-answer pairs, relevant documents, and history.
        """
        try:
            start_time = time.time()
            executor = LogicExecutor(
                query, self.project_id, self.schema,
                kg_retriever=self.kg_retriever,
                chunk_retriever=self.chunk_retriever,
                std_schema=self.std_schema,
                el=self.el,
                text_similarity=self.text_similarity,
                dsl_runner=DslRunnerOnGraphStore(self.project_id, self.schema, LogicFormConfiguration({
                    "KAG_PROJECT_ID": self.project_id,
                    "KAG_PROJECT_HOST_ADDR": self.host_addr
                })),
                generator=self.generator,
                report_tool=self.report_tool,
                req_id=generate_random_string(10)
            )
            kg_qa_result, kg_graph, history = executor.execute(lf_nodes, query)
            logger.info(
                f"{executor.req_id} call_kb_paths cost={time.time() - start_time} kg_path={kg_graph.to_answer_path()}"
            )
        except Exception as e:
            logger.warning(f"lf_retriever {query} lf failed {str(e)}", exc_info=True)
            history = []
            kg_qa_result = []

        docs = []
        sub_qa_pair = []
        if history:
            sub_qa_pair, docs_set = self._process_history(history)
            docs = self._flat_passages_set(docs_set)
        if len(docs) == 0 and len(sub_qa_pair) == 0 and self.chunk_retriever:
            cur_step_recall_docs = self.chunk_retriever.recall_docs(query)
            history.append({'docs': cur_step_recall_docs})
            docs = self._flat_passages_set([cur_step_recall_docs])
        if len(docs) != 0:
            self.last_iter_docs = docs
        return ",".join(kg_qa_result), sub_qa_pair, docs, history
