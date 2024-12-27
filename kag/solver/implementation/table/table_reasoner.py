from typing import List

from kag.examples.finstate.solver.impl.spo_generator import SPOGenerator
from kag.examples.finstate.solver.impl.spo_lf_planner import SPOLFPlanner
from kag.interface.solver.kag_reasoner_abc import KagReasonerABC
from kag.interface.solver.lf_planner_abc import LFPlannerABC
from kag.solver.implementation.default_kg_retrieval import KGRetrieverByLlm
from kag.solver.implementation.default_lf_planner import DefaultLFPlanner
from kag.solver.implementation.default_reasoner import DefaultReasoner
from kag.solver.implementation.table.search_tree import SearchTree, SearchTreeNode
from kag.solver.logic.core_modules.lf_solver import LFSolver
from kag.common.llm.client import LLMClient
from kag.common.base.prompt_op import PromptOp
from kag.solver.implementation.table.retrieval_agent import RetrievalAgent
from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool
from kag.solver.implementation.table.python_coder import PythonCoderAgent


class TableReasoner(KagReasonerABC):
    """
    table reasoner
    """

    def __init__(
            self, lf_planner: LFPlannerABC = None, lf_solver: LFSolver = None, **kwargs
    ):
        super().__init__(lf_planner=lf_planner, lf_solver=lf_solver, **kwargs)
        self.kwargs = kwargs

        self.logic_form_plan_prompt = PromptOp.load(self.biz_scene, "logic_form_plan")(
            language=self.language
        )

        self.resp_generator = PromptOp.load(self.biz_scene, "resp_generator")(
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
        history = SearchTree(question)

        # 上报root
        self.report_pipleline(history)

        # get what we have in KG
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
                    if "i don't know" in node.answer.lower():
                        break
                    continue
                history.add_now_procesing_ndoe(node)

                # 新的子问题出来了
                self.report_pipleline(history)

                # answer subquestion
                sub_answer = None
                if "Retrieval" == func_str:
                    sub_answer = self._call_retravel_func(question, node)
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
            {"memory": str(history), "question": history.root_node.question},
            self.resp_generator,
            with_except=True,
        )
        self.report_pipleline(history, final_answer)
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
        }
        sub_question_list = llm.invoke(
            variables=variables,
            prompt_op=self.logic_form_plan_prompt,
            with_except=True,
        )
        history.set_now_plan(sub_question_list)
        return sub_question_list

    def _call_spo_retravel_func(self, query):
        lf_planner = SPOLFPlanner()
        lf_solver = LFSolver(
            kg_retriever=KGRetrieverByLlm(),
        )
        reason = DefaultReasoner(
            lf_planner=lf_planner,
            lf_solver=lf_solver,
        )
        resp = SolverPipeline(
            reasoner=reason,
            generator=SPOGenerator()
        )
        answer, trace_log = resp.run(query)
        return answer, trace_log

    def _call_retravel_func(self, init_question, node: SearchTreeNode):

        agent = RetrievalAgent(
            init_question=init_question, question=node.question, **self.kwargs
        )
        answer, docs = agent.answer()
        node.answer = answer
        node.answer_desc = docs

        res, trace_log = self._call_spo_retravel_func(init_question)
        if res.lower() != "i don't know":
            return res
        return answer

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

    def report_pipleline(self, history: SearchTree, final_answer: str = None):
        """
        report search tree
        """
        pipeline = history.convert_to_pipleline(final_anser=final_answer)
        if self.report_tool is not None:
            self.report_tool.report_ca_pipeline(pipeline)
