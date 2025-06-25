import sys
import os
import logging
import json
import re
import random
from typing import List

from kag.common.benchmarks.evaluate import Evaluate


from kag.common.registry import import_modules_from_path
from kag.common.conf import KAG_CONFIG


from kag.examples.finqa.reasoner.finqa_reasoner import FinQAReasoner
from kag.examples.finqa.reasoner.finqa_lf_planner import FinQALFPlanner
from kag.examples.finqa.reasoner.finqa_lf_executor import FinQALFExecutor
from kag.examples.finqa.reasoner.finqa_generator import FinQAGenerator
from kag.examples.finqa.reasoner.finqa_chunk_retriever import FinQAChunkRetriever
from kag.examples.finqa.reasoner.finqa_memory import FinQAMemory
from kag.examples.finqa.reasoner.finqa_reflector import FinQAReflector
from kag.examples.finqa.solver.prompt.logic_form_plan import LogicFormPlanPrompt
from kag.examples.finqa.solver.prompt.resp_generator import FinQARespGenerator
from kag.examples.finqa.solver.prompt.expression_builder import FinQAExpressionBuildr
from kag.examples.finqa.solver.prompt.solve_question_without_spo import (
    SolveQuestionWithOutSPO,
)
from kag.examples.finqa.solver.prompt.rerank_chunks import TableRerankChunksPrompt2
from kag.examples.finqa.solver.prompt.question_classify import FinQAQuestionClassify
from kag.examples.finqa.solver.prompt.finqa_reflect_prompt import FinQAReflectQuestion
from kag.examples.finqa.solver.prompt.math_select_prompt import MathSelectPrompt

from kag.examples.finqa.reasoner.finqa_solver_pipeline import FinQASolverPipeline


def qa(question, file_name, _i, _id):
    resp = FinQASolverPipeline.from_config(
        KAG_CONFIG.all_config["finqa_solver_pipeline"]
    )
    from kag.interface.common.kv_store import KVStore
    KVStore.disable = False
    answer, traceLog = resp.run(question, file_name=file_name)
    try:
        # print(json.dumps(traceLog, ensure_ascii=False))
        code = ""
        question = ""
        memory = ""
        try:
            code = traceLog[-1]["code"]
            question = traceLog[-1]["present_instruction"]
            memory = traceLog[-1]["present_memory"]
        except:
            pass
        print(
            f"finqa_processing_log\ni={_i}\nid={_id}\nquestion={question}\n<|memory|>\n{memory}\n<|memory|>\n<|code|>\n{code}\n<|code|>"
        )
    except:
        pass
    return str(answer)


class FinQAEvaluate(Evaluate):

    def check(self, prediction: str, answer: str, exe_ans: str):
        """
        prediction和exe_ans进行比较
        """

        prediction = prediction.strip()
        try:
            # 1. 带有%号的，去除%，数值除以100
            if prediction.endswith("%"):
                prediction = prediction.strip("%")
                prediction = str(float(prediction) / 100)
        except:
            pass

        answer = answer.strip()
        exe_ans = exe_ans.strip()

        if not self.is_float(prediction):
            return super().getBenchMark([prediction], [exe_ans])

        # 比较prediction和exe_ans完全相等
        if self.is_close_rel(exe_ans, prediction):
            return super().getBenchMark(["em"], ["em"])
        elif self.is_percentage_close(exe_ans, prediction):
            return super().getBenchMark(["em"], ["em"])
        elif self.is_float(answer.strip("%")) and self.is_close_rel(
            answer.strip("%"), prediction
        ):
            return super().getBenchMark(["em"], ["em"])
        return super().getBenchMark([prediction], [exe_ans])

    def is_float(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def is_close_rel(self, a, b, rel_tol=1e-9):
        a, b = self.round_to_smaller_precision(a, b)
        a = float(a)
        b = float(b)
        return abs(a - b) < rel_tol * max(abs(a), abs(b))

    def is_percentage_close(self, a, b, rel_tol=1e-9):
        b = str(float(b) / 100)
        a, b = self.round_to_smaller_precision(a, b)
        a = float(a)
        b = float(b)
        return abs(a - b) < rel_tol * max(abs(a), abs(b))

    def round_to_smaller_precision(self, num1: str, num2: str) -> (str, str):
        """
        四舍五入两个数字到较小的精度。
        """

        def get_precision(num: str) -> int:
            if "." in num:
                return len(num.split(".")[1])
            return 0

        num1 = str(abs(float(num1)))
        num2 = str(abs(float(num2)))

        precision1 = get_precision(num1)
        precision2 = get_precision(num2)
        smaller_precision = min(precision1, precision2)
        rounded_num1 = round(float(num1), smaller_precision)
        rounded_num2 = round(float(num2), smaller_precision)
        return (
            f"{rounded_num1:.{smaller_precision}f}",
            f"{rounded_num2:.{smaller_precision}f}",
        )

    def is_same_sign(self, str1, str2):
        num1 = float(str1)
        num2 = float(str2)
        # 判断正负号是否相同
        return (num1 >= 0 and num2 >= 0) or (num1 < 0 and num2 < 0)


def load_finqa_data_list() -> map:
    """
    load data
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = os.path.join(current_dir, "..", "builder", "data", "test.json")
    with open(file_name, "r", encoding="utf-8") as f:
        data_list = json.load(f)
    print("finqa data list len " + str(len(data_list)))
    for _idx, data in enumerate(data_list):
        data["index"] = _idx
    return data_list


if __name__ == "__main__":
    process_idx = 0
    all_idx = 1
    if len(sys.argv) >= 3:
        process_idx = int(sys.argv[1])
        all_idx = int(sys.argv[2])
    _finqa_data_list = load_finqa_data_list()
    evaObj = FinQAEvaluate()
    total_metrics = {
        "em": 0.0,
        "f1": 0.0,
        "answer_similarity": 0.0,
        "processNum": 0,
    }
    debug_index = None

    # if debug_index is None:
    #     # 进行采样测试
    #     test_count = 200
    #     _finqa_data_list = random.sample(_finqa_data_list, test_count)

    error_question_map = {"error": [], "no_answer": [], "system_error": []}
    for _item in _finqa_data_list:
        i = _item["index"]
        if i % all_idx != process_idx:
            continue
        if debug_index is not None:
            if i not in debug_index:
                continue
        _id = _item["id"]
        _question = _item["qa"]["question"]
        _answer = str(_item["qa"]["answer"])
        _exe_ans = str(_item["qa"]["exe_ans"])
        try:
            _prediction = qa(
                question=_question, file_name=_item["filename"], _i=i, _id=_id
            )
        except KeyboardInterrupt:
            break
        except:
            logging.exception("qa error")
            _prediction = str(None)
        print("#" * 100)
        metrics = evaObj.check(_prediction, _answer, _exe_ans)

        __error = False
        if metrics["em"] < 0.9:
            __error = True
            if "None" == _prediction:
                error_question_map["system_error"].append((i, _id))
            elif "i don't know" in _prediction.lower():
                error_question_map["no_answer"].append((i, _id))
            else:
                error_question_map["error"].append((i, _id))
        print(
            "index="
            + str(i)
            + ",gold="
            + str(_exe_ans)
            + ",answer="
            + str(_answer)
            + ",prediction="
            + str(_prediction)
            + ",error="
            + str(__error)
        )

        total_metrics["em"] += metrics["em"]
        total_metrics["f1"] += metrics["f1"]
        total_metrics["answer_similarity"] += metrics["answer_similarity"]
        total_metrics["processNum"] += 1

        print(total_metrics)
        print(total_metrics["em"] / total_metrics["processNum"] * 100)
        print("error index list=" + str(error_question_map))
        print("#" * 100)
