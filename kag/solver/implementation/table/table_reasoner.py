import os
import time
from typing import List
import logging
from concurrent.futures import ThreadPoolExecutor

from kag.examples.finstate.solver.impl.chunk_lf_planner import ChunkLFPlanner
from kag.examples.finstate.solver.impl.spo_generator import SPOGenerator
from kag.examples.finstate.solver.impl.spo_lf_planner import SPOLFPlanner
from kag.examples.finstate.solver.impl.spo_memory import SpoMemory
from kag.examples.finstate.solver.impl.spo_reflector import SPOReflector
from kag.interface.solver.kag_reasoner_abc import KagReasonerABC
from kag.interface.solver.lf_planner_abc import LFPlannerABC
from kag.solver.implementation.default_kg_retrieval import KGRetrieverByLlm
from kag.solver.implementation.default_reasoner import DefaultReasoner
from kag.solver.implementation.lf_chunk_retriever import LFChunkRetriever
from kag.solver.implementation.table.search_tree import SearchTree, SearchTreeNode
from kag.solver.logic.core_modules.lf_solver import LFSolver
from kag.common.llm.client import LLMClient
from kag.common.base.prompt_op import PromptOp
from kag.solver.implementation.table.retrieval_agent import TableRetrievalAgent
from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool
from kag.solver.implementation.table.python_coder import PythonCoderAgent

logger = logging.getLogger()


class TableReasoner(KagReasonerABC):
    """
    table reasoner
    """

    DOMAIN_KNOWLEDGE_INJECTION = "在当前会话注入领域知识"
    DOMAIN_KNOWLEDGE_QUERY = "返回当前会话的领域知识"

    def __init__(
        self, lf_planner: LFPlannerABC = None, lf_solver: LFSolver = None, **kwargs
    ):
        super().__init__(lf_planner=lf_planner, lf_solver=lf_solver, **kwargs)
        self.kwargs = kwargs
        self.session_id = kwargs.get("session_id", 0)
        self.dk = self._query_dk()

        self.logic_form_plan_prompt = PromptOp.load(self.biz_scene, "logic_form_plan_table")(
            language=self.language
        )

        self.resp_generator = PromptOp.load(self.biz_scene, "resp_generator")(
            language=self.language
        )
        self.llm_backup = PromptOp.load(self.biz_scene, "llm_backup")(
            language=self.language
        )
        self.report_tool: ReporterIntermediateProcessTool = kwargs.get(
            "report_tool", None
        )

    def reason(self, question: str):
        """
        Processes a given question by planning and executing logical forms to derive an answer.
        Parameters:
        - question (str): The input question to be processed.
        Returns:
        - solved_answer: The final answer derived from solving the logical forms.
        - supporting_fact: Supporting facts gathered during the reasoning process.
        - history_log: A dictionary containing the history of QA pairs and re-ranked documents.
        """
        history = SearchTree(question, self.dk)

        if question.startswith(TableReasoner.DOMAIN_KNOWLEDGE_INJECTION):
            self._save_dk(question, history)
            return "done"
        elif question.startswith(TableReasoner.DOMAIN_KNOWLEDGE_QUERY):
            return self._query_dk_and_report(history)

        # 上报root
        self.report_pipleline(history)

        # get what we have in KG
        # kg_content = "阿里巴巴2025财年年度中期报告"
        # TODO
        kg_content = ""

        try_times = 3
        while try_times > 0:
            try_times -= 1
            sub_question_faild = False

            # logic form planing
            sub_question_list = self._get_sub_question_list(
                history=history, kg_content=kg_content
            )
            history.set_now_plan(sub_question_list)

            print("subquestion_list=" + str(sub_question_list))

            for sub_question in sub_question_list:
                sub_q_str = sub_question["sub_question"]
                func_str = sub_question["process_function"]

                node = SearchTreeNode(sub_q_str, func_str)
                if history.has_node(node=node):
                    node: SearchTreeNode = history.get_node_in_graph(node)
                    if node.answer is None or "i don't know" in node.answer.lower():
                        break
                    continue
                history.add_now_procesing_ndoe(node)

                # 新的子问题出来了
                self.report_pipleline(history)

                # answer subquestion
                sub_answer = None
                if "Retrieval" == func_str:
                    sub_answer = self._call_retravel_func(question, node, history)
                elif "PythonCoder" == func_str:
                    sub_answer = self._call_python_coder_func(
                        init_question=question, node=node, history=history
                    )
                else:
                    raise RuntimeError(f"unsupported agent {func_str}")

                # 子问题答案
                self.report_pipleline(history)

                print("subquestion=" + str(sub_q_str) + ",answer=" + str(sub_answer))
                # reflection
                if sub_answer is None or "i don't know" in sub_answer.lower():
                    # 重新进行规划
                    sub_question_faild = True
                    break
            if sub_question_faild:
                # logic form planing
                sub_question_list = self._get_sub_question_list(
                    history=history, kg_content=kg_content
                )
                history.set_now_plan(sub_question_list)
                continue
            else:
                # 所有子问题都被解答
                break
        final_answer = "I don't know"
        # 总结答案
        llm: LLMClient = self.llm_module
        final_answer = llm.invoke(
            {
                "memory": str(history),
                "question": history.root_node.question,
                "dk": history.dk,
            },
            self.resp_generator,
            with_except=True,
        )
        final_answer = str(final_answer)  # fix 'float' object has no attribute 'lower'
        final_answer_form_llm = False
        if final_answer is None or "i don't know" in final_answer.lower():
            # 大模型兜底
            final_answer_form_llm = True
            final_answer = llm.invoke(
                {"question": history.root_node.question, "dk": history.dk},
                self.llm_backup,
                with_except=True,
            )
        self.report_pipleline(history, final_answer, final_answer_form_llm)
        return final_answer

    def _get_sub_question_list(self, history: SearchTree, kg_content: str):
        llm: LLMClient = self.llm_module
        history_str = None
        if history.now_plan is not None:
            history.set_now_plan(None)
            history_str = str(history)
        variables = {
            "input": history.root_node.question,
            "kg_content": kg_content,
            "history": history_str,
            "dk": history.dk,
        }
        sub_question_list = llm.invoke(
            variables=variables,
            prompt_op=self.logic_form_plan_prompt,
            with_except=True,
        )
        history.set_now_plan(sub_question_list)
        return sub_question_list

    def _call_chunk_retravel_func(self, query):
        lf_planner = ChunkLFPlanner(
            KAG_PROJECT_ID=self.project_id, KAG_PROJECT_HOST_ADDR=self.host_addr
        )
        lf_solver = LFSolver(
            chunk_retriever=LFChunkRetriever(
                KAG_PROJECT_ID=self.project_id, KAG_PROJECT_HOST_ADDR=self.host_addr
            ),
            KAG_PROJECT_ID=self.project_id,
            KAG_PROJECT_HOST_ADDR=self.host_addr,
        )
        reason = DefaultReasoner(
            lf_planner=lf_planner,
            lf_solver=lf_solver,
            KAG_PROJECT_ID=self.project_id,
            KAG_PROJECT_HOST_ADDR=self.host_addr,
        )
        resp = SolverPipeline(
            max_run=1,
            reflector=SPOReflector(
                KAG_PROJECT_ID=self.project_id, KAG_PROJECT_HOST_ADDR=self.host_addr
            ),
            reasoner=reason,
            generator=SPOGenerator(
                KAG_PROJECT_ID=self.project_id, KAG_PROJECT_HOST_ADDR=self.host_addr
            ),
            memory=SpoMemory(
                KAG_PROJECT_ID=self.project_id, KAG_PROJECT_HOST_ADDR=self.host_addr
            ),
        )
        answer, trace_log = resp.run(query)
        return answer, trace_log

    def _call_spo_retravel_func(self, query):
        lf_planner = SPOLFPlanner(
            KAG_PROJECT_ID=self.project_id, KAG_PROJECT_HOST_ADDR=self.host_addr
        )
        lf_solver = LFSolver(
            kg_retriever=KGRetrieverByLlm(
                KAG_PROJECT_ID=self.project_id, KAG_PROJECT_HOST_ADDR=self.host_addr
            ),
            chunk_retriever=LFChunkRetriever(
                KAG_PROJECT_ID=self.project_id, KAG_PROJECT_HOST_ADDR=self.host_addr
            ),
            KAG_PROJECT_ID=self.project_id,
            KAG_PROJECT_HOST_ADDR=self.host_addr,
        )
        reason = DefaultReasoner(
            lf_planner=lf_planner,
            lf_solver=lf_solver,
            KAG_PROJECT_ID=self.project_id,
            KAG_PROJECT_HOST_ADDR=self.host_addr,
        )
        resp = SolverPipeline(
            max_run=1,
            reflector=SPOReflector(
                KAG_PROJECT_ID=self.project_id, KAG_PROJECT_HOST_ADDR=self.host_addr
            ),
            reasoner=reason,
            generator=SPOGenerator(
                KAG_PROJECT_ID=self.project_id, KAG_PROJECT_HOST_ADDR=self.host_addr
            ),
            memory=SpoMemory(
                KAG_PROJECT_ID=self.project_id, KAG_PROJECT_HOST_ADDR=self.host_addr
            ),
        )
        solved_answer, supporting_fact, history_log = reason.reason(query)
        if "history" in history_log and len(history_log["history"]) > 0:
            answer = history_log["history"][-1].get("sub_answer", "I don't know")
        else:
            answer = "I don't know"
        return answer, [history_log]

    def _call_retravel_func(
        self, init_question, node: SearchTreeNode, history: SearchTree
    ):
        table_retrical_agent = TableRetrievalAgent(
            init_question=init_question,
            question=node.question,
            dk=history.dk,
            **self.kwargs,
        )
        answer_history = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            # 两路召回同时做符号求解
            futures = [
                executor.submit(table_retrical_agent.symbol_solver),
                executor.submit(self._call_spo_retravel_func, node.question),
            ]

            # 等待任务完成并获取结果
            for i, future in enumerate(futures):
                if 0 == i:
                    res, trace_log = future.result()
                    answer_history.append({"res": res, "trace_log": trace_log})
                    if "i don't know" not in res.lower():
                        self.update_node(node, res, trace_log)
                        return res
                elif 1 == i:
                    res, trace_log = future.result()
                    answer_history.append({"res": res, "trace_log": trace_log})
                    if "i don't know" not in res.lower():
                        self.update_node(node, res, trace_log)
                        return res
            # 同时进行chunk求解
            futures = [
                executor.submit(table_retrical_agent.answer),
                # executor.submit(self._call_chunk_retravel_func, node.question),
            ]
            for i, future in enumerate(futures):
                if 0 == i:
                    try:
                        res, trace_log = future.result()
                        answer_history.append({"res": res, "trace_log": trace_log})
                        if "i don't know" not in res.lower():
                            self.update_node(node, res, trace_log)
                            return res
                    except Exception as e:
                        logger.warning(f"table chunk failed {e}", exc_info=True)
        answer = "\n".join(list(set([h["res"] for h in answer_history])))
        trace_log = self._merge_trace_log([h["trace_log"] for h in answer_history])
        self.update_node(node, answer, trace_log)
        node.answer = answer
        return node.answer

    def _merge_trace_log(self, trace_logs):
        context = []
        sub_graphs = []
        for trace_log in trace_logs:
            if trace_log is None or len(trace_log) < 1:
                continue
            if "report_info" not in trace_log[0]:
                continue
            context += trace_log[0]["report_info"]["context"]
            if trace_log[0]["report_info"].get("sub_graph", None):
                sub_graphs += trace_log[0]["report_info"]["sub_graph"]
        return [{"report_info": {"context": context, "sub_graph": sub_graphs}}]

    def update_node(self, node, res, trace_log):
        if len(trace_log) == 1 and "report_info" in trace_log[0]:
            node.answer = res
            if node.answer_desc is None:
                node.answer_desc = ""
            node.answer_desc += "\n".join(trace_log[0]["report_info"]["context"])
            if trace_log[0]["report_info"]["sub_graph"]:
                node.sub_graph = trace_log[0]["report_info"]["sub_graph"]

    def _call_python_coder_func(
        self, init_question, node: SearchTreeNode, history: SearchTree
    ):
        agent = PythonCoderAgent(init_question, node.question, history, **self.kwargs)
        sub_answer, code = agent.answer()
        node.answer = sub_answer
        node.answer_desc = self._process_coder_desc(code)
        return sub_answer

    def _process_coder_desc(self, coder_desc: str):
        # 拆分文本为行
        lines = coder_desc.splitlines()
        # 过滤掉包含 'print' 的行
        filtered_lines = [line for line in lines if "print(" not in line]
        # 将过滤后的行重新组合为文本
        return "\n".join(filtered_lines)

    def report_pipleline(
        self,
        history: SearchTree,
        final_answer: str = None,
        final_answer_form_llm: bool = False,
    ):
        """
        report search tree
        """
        pipeline = history.convert_to_pipleline(
            final_answer=final_answer, final_answer_form_llm=final_answer_form_llm
        )
        if self.report_tool is not None:
            self.report_tool.report_ca_pipeline(pipeline)

    def _save_dk(self, dk: str, history: SearchTree):
        dk = dk.strip(TableReasoner.DOMAIN_KNOWLEDGE_INJECTION)
        dk = dk.strip().strip("\n")

        file_name = f"/tmp/dk/{self.session_id}"
        os.makedirs(os.path.dirname(file_name), exist_ok=True)

        # 打开文件并写入字符串
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(dk)
        self.report_pipleline(history, "done", True)

    def _query_dk(self) -> str:
        file_name = f"/tmp/dk/{self.session_id}"
        if not os.path.exists(file_name):
            return None
        with open(file_name, "r", encoding="utf-8") as file:
            dk = file.read()
        return dk

    def _query_dk_and_report(self, history) -> str:
        dk = self._query_dk()
        if dk is None:
            self.report_pipleline(history, "当前会话没有设置领域知识", True)
        else:
            self.report_pipleline(history, dk, True)
