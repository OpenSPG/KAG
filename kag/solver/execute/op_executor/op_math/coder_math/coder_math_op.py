import os
import re
import subprocess
import sys
import tempfile
from typing import Dict

from kag.interface import LLMClient
from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import MathNode
from kag.solver.utils import init_prompt_with_fallback


class CoderMathOp(OpExecutor):
    def __init__(self, schema: SchemaUtils,**kwargs):
        super().__init__(schema, **kwargs)
        self.expression_builder =init_prompt_with_fallback("expression_builder", self.biz_scene)
    def _run_onetime(self, question, content, error: str):
        llm: LLMClient = self.llm_module
        python_code = llm.invoke(
            {
                "question": question,
                "context": str(content),
                "error": error,
            },
            self.expression_builder,
        )
        if not python_code:
            raise RuntimeError("python code generate failed")

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

    def execute_with_retry(self, logic_node: MathNode, kg_graph: KgGraph, process_info: Dict, req_id: str, param: dict):
        content = logic_node.content
        nodes_alias = kg_graph.nodes_alias
        try:
            content_l = re.findall('`(.*?)`', content)
        except Exception as e:
            # breakpoint()
            pass
        contents = []
        for c in content_l:
            if c in nodes_alias and c in kg_graph.entity_map.keys():
                values = kg_graph.entity_map[c]
                c = str(values)
            contents.append(c)
        history_qa_pair = process_info.get("sub_qa_pair", [])
        contents = '\n'.join(contents) if contents else history_qa_pair
        target = logic_node.target if logic_node.target else logic_node.sub_query
        try_times = 3
        error = None
        while try_times > 0:
            try_times -= 1
            rst, run_error, code = self._run_onetime(target, contents, error)
            if rst is not None:
                process_info[logic_node.sub_query]['debug'] = {
                    'code': code,
                    'rst': rst,
                    'error': run_error
                }
                return rst
            error = f"code:\n{code}\nerror:\n{run_error}"
            print("code=" + str(code) + ",error=" + str(run_error))
            if 'debug'  not in process_info[logic_node.sub_query]:
                process_info[logic_node.sub_query]['debug'] = []
            process_info[logic_node.sub_query]['debug'] .append({
                'code': code,
                'rst': rst,
                'error': run_error
            })
        return "I don't know"
    
    def executor(
        self,
        nl_query: str,
        logic_node: MathNode,
        req_id: str,
        kg_graph: KgGraph,
        process_info: dict,
        param: dict,
    ) -> Dict:
        result = self.execute_with_retry(logic_node, kg_graph, process_info, req_id, param)
        return  {
            "if_answered": False if "i don't know" in result.lower() else True,
            "answer": result
        }

