import logging
import json
import re
from typing import List

from kag.common.benchmarks.evaluate import Evaluate


from kag.common.registry import import_modules_from_path
from kag.common.conf import KAG_CONFIG

from kag.examples.finqa.builder.indexer import build_finqa_graph, load_finqa_data

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
from kag.examples.finqa.solver.prompt.rerank_chunks import TableRerankChunksPrompt
from kag.examples.finqa.solver.prompt.question_classify import FinQAQuestionClassify
from kag.examples.finqa.solver.prompt.finq_reflect_prompt import FinQAReflectQuestion
from kag.examples.finqa.solver.prompt.math_select_prompt import MathSelectPrompt

from kag.examples.finqa.reasoner.finqa_solver_pipeline import FinQASolverPipeline


def qa(question, _i, _id):
    resp = FinQASolverPipeline.from_config(
        KAG_CONFIG.all_config["finqa_solver_pipeline"]
    )
    answer, traceLog = resp.run(question)
    try:
        print(json.dumps(traceLog, ensure_ascii=False))
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
        try:
            float(exe_ans)
            float(prediction)
        except:
            # yes or no
            return super().getBenchMark([prediction], [exe_ans])

        try:
            # fix %
            prediction = prediction.strip()
            if prediction.endswith("%"):
                prediction = prediction.strip("%")
                prediction = str(float(prediction) / 100)

            answer = answer.strip()
            if answer.endswith("%"):
                if not self.is_same_sign(answer.strip("%"), exe_ans):
                    # 修复百分比问题中的正负号
                    answer = str(abs(float(answer.strip("%")))) + "%"
                    exe_ans = str(abs(float(exe_ans)))
                    prediction = str(abs(float(prediction)))
                tmp_answer, tmp_exe_ans = self.round_to_smaller_precision(
                    answer.strip("%"), exe_ans
                )
                if self.is_close_rel(tmp_answer, tmp_exe_ans):
                    exe_ans = str(float(exe_ans) / 100)
        except:
            pass

        exe_ans, prediction = self.round_to_smaller_precision(exe_ans, prediction)
        if self.is_close_rel(exe_ans, prediction) or self.is_percentage_close(
            exe_ans, prediction
        ):
            return super().getBenchMark(["em"], ["em"])

        return super().getBenchMark([prediction], [exe_ans])

    def is_close_rel(self, a, b, rel_tol=1e-9):
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


if __name__ == "__main__":
    _finqa_file_to_qa_map = load_finqa_data()
    evaObj = FinQAEvaluate()
    total_metrics = {
        "em": 0.0,
        "f1": 0.0,
        "answer_similarity": 0.0,
        "processNum": 0,
    }
    debug_index = None
    error_question_map = {"error": [], "no_answer": [], "system_error": []}
    for file_name, _item_list in _finqa_file_to_qa_map.items():
        if debug_index is not None:
            index_set = set([_item["index"] for _item in _item_list])
            intersection = index_set.intersection(set(debug_index))
            if len(intersection) <= 0:
                continue

        build_finqa_graph(_item_list[0])

        for _item in _item_list:
            i = _item["index"]
            if debug_index is not None:
                if i not in debug_index:
                    continue
            _id = _item["id"]
            _question = _item["qa"]["question"]
            _answer = str(_item["qa"]["answer"])
            _exe_ans = str(_item["qa"]["exe_ans"])
            try:
                _prediction = qa(question=_question, _i=i, _id=_id)
            except KeyboardInterrupt:
                break
            except:
                logging.exception("qa error")
                _prediction = str(None)
            print("#" * 100)
            print(
                "index="
                + str(i)
                + ",gold="
                + str(_exe_ans)
                + ",prediction="
                + str(_prediction)
            )
            metrics = evaObj.check(_prediction, _answer, _exe_ans)

            if metrics["em"] < 0.9:
                if "None" == _prediction:
                    error_question_map["system_error"].append((i, _id))
                elif "i don't know" in _prediction.lower():
                    error_question_map["no_answer"].append((i, _id))
                else:
                    error_question_map["error"].append((i, _id))

            total_metrics["em"] += metrics["em"]
            total_metrics["f1"] += metrics["f1"]
            total_metrics["answer_similarity"] += metrics["answer_similarity"]
            total_metrics["processNum"] += 1

            print(total_metrics)
            print(total_metrics["em"] / total_metrics["processNum"] * 100)
            print("error index list=" + str(error_question_map))
            print("#" * 100)
