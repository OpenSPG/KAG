import logging
from typing import List, Dict

import os
import concurrent.futures
import re
import subprocess
import sys
import tempfile
from typing import Dict, List

from kag.interface import LLMClient
from kag.interface.solver.base_model import LFPlan
from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import MathNode
from kag.solver.utils import init_prompt_with_fallback

from tenacity import retry, stop_after_attempt

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import LLMClient
from kag.interface.solver.execute.lf_executor_abc import LFExecutorABC
from kag.interface.solver.execute.lf_sub_query_merger_abc import LFSubQueryResMerger
from kag.solver.execute.op_executor.op_deduce.deduce_executor import DeduceExecutor
from kag.solver.execute.op_executor.op_math.math_executor import MathExecutor
from kag.solver.execute.op_executor.op_output.output_executor import OutputExecutor
from kag.solver.execute.op_executor.op_retrieval.retrieval_executor import (
    RetrievalExecutor,
)
from kag.interface.solver.base_model import LFExecuteResult, LFPlan, SubQueryResult
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.utils import generate_random_string
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.retriever.chunk_retriever import ChunkRetriever
from kag.solver.retriever.exact_kg_retriever import ExactKgRetriever
from kag.solver.retriever.fuzzy_kg_retriever import FuzzyKgRetriever
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool
from kag.solver.execute.default_lf_executor import DefaultLFExecutor
from typing import Union, Dict, List

from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.interface.solver.base_model import LogicNode, LFPlan
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import MathNode

from kag.examples.finqa.reasoner.common import (
    get_history_context_info_list,
    get_history_context_str,
    get_execute_context,
    get_all_recall_docs,
)


logger = logging.getLogger()


class FinQACoderMathOp(OpExecutor):
    def __init__(self, schema: SchemaUtils, **kwargs):
        super().__init__(schema, **kwargs)
        self.expression_builder = init_prompt_with_fallback(
            "expression_builder", self.biz_scene
        )

        self.math_select = init_prompt_with_fallback("math_select", self.biz_scene)

    def _run_onetime(self, question, content, error: str, examples):
        llm: LLMClient = self.llm_module
        python_code = llm.invoke(
            {
                "question": question,
                "context": str(content),
                "error": error,
                "examples": examples,
            },
            self.expression_builder,
        )
        if not python_code:
            raise RuntimeError("python code generate failed")

        if "I don't know".lower() in python_code.lower():
            return "I don't know", None, python_code

        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_file:
            temp_file.write(python_code.encode("utf-8"))
            temp_file_path = temp_file.name

        try:
            # 获取当前Python环境的可执行文件路径
            python_executable = sys.executable
            # 使用subprocess模块来执行临时文件
            result = subprocess.run(
                [python_executable, temp_file_path], capture_output=True, text=True
            )
        finally:
            # 清理临时文件
            os.remove(temp_file_path)

        # 获取捕获的输出和错误信息
        stdout_value = result.stdout
        stderr_value = result.stderr
        if len(stderr_value) > 0:
            return None, stderr_value, python_code
        return stdout_value, None, python_code

    def execute_with_retry(
        self,
        i: int,
        lf_plan: LFPlan,
        process_info: Dict,
    ):
        process_info[i] = {}
        execute_rst_list: List[LFExecuteResult] = process_info["execute_rst_list"]
        question = process_info["goal"]
        content_str = get_history_context_str(
            get_execute_context(question=question, execute_rst_list=execute_rst_list)
        )
        example_list = process_info["examples"]
        target = question
        if 0 == i:
            example_list = [example_list[i] for i in [0, 1, 2]]
        elif 1 == i:
            example_list = [example_list[i] for i in [0, 1, 2]]
        elif 2 == i:
            example_list = [example_list[i] for i in [0, 1, 2]]
            target = lf_plan.query
        example_str = "\n\n".join(example_list)
        try_times = 3
        error = None
        while try_times > 0:
            try_times -= 1
            rst, run_error, code = self._run_onetime(
                target, content_str, error, example_str
            )
            if rst is not None:
                process_info[i]["debug"] = {
                    "code": code,
                    "rst": rst,
                    "error": run_error,
                }
                return rst, code
            error = f"code:\n{code}\nerror:\n{run_error}"
            print("code=" + str(code) + ",error=" + str(run_error))
            if "debug" not in process_info[i]:
                process_info[i]["debug"] = []
            process_info[i]["debug"].append(
                {"code": code, "rst": rst, "error": run_error}
            )
        return "I don't know", code

    def executor_with_out_vote(
        self,
        nl_query: str,
        lf_plan: LFPlan,
        req_id: str,
        kg_graph: KgGraph,
        process_info: dict,
        history: List[LFPlan],
        param: dict,
    ) -> Dict:
        ans, code = self.execute_with_retry(i=0, lf_plan=lf_plan, process_info=process_info)
        lf_plan.res.debug_info = {
            "code": code,
            "rst": ans,
            "error": "",
        }
        return {
            "if_answered": False if "i don't know" in ans.lower() else True,
            "answer": ans,
        }

    def executor(
        self,
        nl_query: str,
        lf_plan: LFPlan,
        req_id: str,
        kg_graph: KgGraph,
        process_info: dict,
        history: List[LFPlan],
        param: dict,
    ) -> Dict:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as _executor:
            futures = [
                _executor.submit(self.execute_with_retry, i, lf_plan, process_info)
                for i in range(3)
            ]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        answers_str = ""
        as_index = 0
        for ans, code in results:
            answers_str += f"### answer {as_index}\n```python{code}```\noutput={ans}\n\n"
            as_index += 1
        llm: LLMClient = self.llm_module
        execute_rst_list: List[LFExecuteResult] = process_info["execute_rst_list"]
        question = process_info["goal"]
        content_str = get_all_recall_docs(execute_rst_list=execute_rst_list)
        content_str = "\n".join(content_str)
        select_index = llm.invoke(
            {
                "question": question,
                "context": content_str,
                "answers": answers_str,
            },
            self.math_select,
            with_json_parse=False,
            with_except=True,
        )
        ans, code = results[select_index]

        lf_plan.res.debug_info = {
            "code": code,
            "rst": ans,
            "error": "",
        }
        return {
            "if_answered": False if "i don't know" in ans.lower() else True,
            "answer": ans,
        }


class FinQAMathExecutor(OpExecutor):
    def __init__(self, schema: SchemaUtils, **kwargs):
        super().__init__(schema, **kwargs)
        self.op_mapping = {
            "math": FinQACoderMathOp(self.schema, **kwargs),
        }

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, MathNode)

    @retry(stop=stop_after_attempt(3))
    def executor(
        self,
        nl_query: str,
        lf_plan: LFPlan,
        req_id: str,
        kg_graph: KgGraph,
        process_info: dict,
        history: List[LFPlan],
        param: dict,
    ) -> Dict:
        math_node: MathNode = lf_plan.lf_node
        kg_graph.alias_set.append(math_node.alias_name)
        result = self.op_mapping[lf_plan.lf_node.operator].executor(
            nl_query, lf_plan, req_id, kg_graph, process_info, history, param
        )
        if_answered = result["if_answered"]
        answer = result["answer"]
        if if_answered:
            kg_graph.add_answered_alias(math_node.alias_name, answer)
        process_info[lf_plan.lf_node.sub_query]["kg_answer"] = answer
        process_info[lf_plan.lf_node.sub_query]["if_answered"] = if_answered
        lf_plan.res.sub_answer = answer
        lf_plan.res.if_answered = if_answered

        return process_info


@LFExecutorABC.register("finqa_lf_executor", as_default=True)
class FinQALFExecutor(DefaultLFExecutor):
    def __init__(
        self,
        merger: LFSubQueryResMerger,
        exact_kg_retriever: ExactKgRetriever = None,
        fuzzy_kg_retriever: FuzzyKgRetriever = None,
        chunk_retriever: ChunkRetriever = None,
        force_chunk_retriever: bool = True,
        llm_client: LLMClient = None,
        **kwargs,
    ):
        super().__init__(
            merger=merger,
            exact_kg_retriever=exact_kg_retriever,
            fuzzy_kg_retriever=fuzzy_kg_retriever,
            chunk_retriever=chunk_retriever,
            force_chunk_retriever=force_chunk_retriever,
            llm_client=llm_client,
            **kwargs,
        )

        self.math_executor = FinQAMathExecutor(schema=self.schema, **self.params)

    def execute(self, query, lf_nodes: List[LFPlan], **kwargs) -> LFExecuteResult:
        self._create_report_pipeline(kwargs.get("report_tool", None), query, lf_nodes)
        process_info = {"kg_solved_answer": [], "sub_qa_pair": []}
        if "process_info" in kwargs:
            process_info = kwargs.pop("process_info")
        kg_graph = KgGraph()
        history = []
        # Process each sub-query.
        for idx, lf in enumerate(lf_nodes):
            res = SubQueryResult()
            res.sub_query = lf.query
            lf.res = res
            process_info[lf.query] = {
                "spo_retrieved": [],
                "doc_retrieved": [],
                "if_answered": False,
                "match_type": "chunk",
                "kg_answer": "",
            }
        for idx, lf in enumerate(lf_nodes):
            sub_result, is_break = self._execute_lf(
                req_id=generate_random_string(10),
                index=idx + 1,
                query=query,
                lf=lf,
                process_info=process_info,
                kg_graph=kg_graph,
                history=history,
                **kwargs,
            )
            lf.res = sub_result
            process_info["sub_qa_pair"].append([lf.query, sub_result.sub_answer])
            history.append(lf)
            if is_break:
                break
        # merge all results
        res = self.merger.merge(query, history)
        res.retrieved_kg_graph = kg_graph
        res.kg_exact_solved_answer = "\n".join(process_info["kg_solved_answer"])
        return res
