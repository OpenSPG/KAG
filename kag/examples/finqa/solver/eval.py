import logging
import json
import re
from typing import List

from kag.common.benchmarks.evaluate import Evaluate

from kag.solver.logic.solver_pipeline import SolverPipeline

from kag.common.registry import import_modules_from_path
from kag.common.conf import KAG_CONFIG

from kag.examples.finqa.builder.indexer import build_finqa_graph, load_finqa_data

from kag.examples.finqa.reasoner.finqa_reasoner import FinQAReasoner
from kag.examples.finqa.reasoner.finqa_lf_planner import FinQALFPlanner
from kag.examples.finqa.reasoner.finqa_lf_executor import FinQALFExecutor
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


def qa(question, _i, _id):
    resp = SolverPipeline.from_config(KAG_CONFIG.all_config["finqa_solver_pipeline"])
    answer, traceLog = resp.run(question)
    try:
        print(json.dumps(traceLog, ensure_ascii=False))
        code = ""
        for sub_q in traceLog[-1]["sub question"]:
            lf_expr = sub_q["lf_expr"]
            if "math" not in lf_expr:
                continue
            code = sub_q["debug_info"]["code"]
        print(
            f"finqa_processing_log\ni={_i}\nid={_id}\n<|memory|>\n{traceLog[-1]['present_memory']}\n<|memory|>\n<|code|>\n{code}\n<|code|>"
        )
    except:
        pass
    return str(answer)


class MultiHerttEvaluate(Evaluate):
    def getBenchMark(self, predictionlist: List[str], goldlist: List[str]):
        new_predictionlist = []
        new_goldlist = []
        # 如果是数值，按照精度进行判断
        for _i, _prediction in enumerate(predictionlist):
            _prediction = str(_prediction)
            gold = str(goldlist[_i])
            try:
                # 结果是纯数值
                gold = str(float(gold))
                if "%" in _prediction:
                    _prediction = _prediction.strip("%")
                    _prediction = str(float(_prediction) / 100)
                gold, _prediction = self.round_to_smaller_precision(gold, _prediction)
                if self.is_close_rel(
                    float(gold), float(_prediction)
                ) or self.is_percentage_close(float(gold), float(_prediction)):
                    new_predictionlist.append("em")
                    new_goldlist.append("em")
                    continue
                new_predictionlist.append(_prediction)
                new_goldlist.append(gold)
            except Exception:
                new_predictionlist.append(_prediction)
                new_goldlist.append(gold)
        return super().getBenchMark(new_predictionlist, new_goldlist)

    def is_close_rel(self, a, b, rel_tol=1e-9):
        return abs(a - b) < rel_tol * max(abs(a), abs(b))

    def is_percentage_close(self, a, b, rel_tol=1e-9):
        b = b / 100
        a, b = self.round_to_smaller_precision(str(a), str(b))
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


if __name__ == "__main__":
    _data_list = load_finqa_data(shuffle=True)
    evaObj = MultiHerttEvaluate()
    total_metrics = {
        "em": 0.0,
        "f1": 0.0,
        "answer_similarity": 0.0,
        "processNum": 0,
    }
    debug_index = None
    error_question_map = {"error": [], "no_answer": [], "system_error": []}
    for _item in _data_list:
        i = _item["index"]
        if debug_index is not None:
            if i not in debug_index:
                continue
        _id = _item["id"]
        _question = _item["qa"]["question"]
        _gold = str(_item["qa"]["exe_ans"])
        try:
            build_finqa_graph(_item)
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
            + str(_gold)
            + ",prediction="
            + str(_prediction)
        )
        metrics = evaObj.getBenchMark([_prediction], [_gold])

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
