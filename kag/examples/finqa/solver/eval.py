import logging
import re
from typing import List

from kag.common.benchmarks.evaluate import Evaluate

from kag.solver.logic.solver_pipeline import SolverPipeline

from kag.common.registry import import_modules_from_path
from kag.common.conf import KAG_CONFIG

from kag.examples.finqa.builder.indexer import build_finqa_graph, load_finqa_data

from kag.examples.finqa.reasoner.finqa_reasoner import FinQAReasoner
from kag.examples.finqa.reasoner.step_lf_planner import StepLFPlanner
from kag.examples.finqa.reasoner.step_lf_executor import StepLFExecutor
from kag.examples.finqa.solver.prompt.logic_form_plan import LogicFormPlanPrompt
from kag.examples.finqa.solver.prompt.rerank_chunks import TableRerankChunksPrompt
from kag.examples.finqa.solver.prompt.resp_generator import FinQARespGenerator


def qa(question, **kwargs):
    resp = SolverPipeline.from_config(KAG_CONFIG.all_config["finqa_solver_pipeline"])
    answer, traceLog = resp.run(question)

    print(f"\n\nso the answer for '{question}' is: {answer}\n\n")  #
    print(traceLog)
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
                if "%" in gold:
                    gold = gold.strip("%")
                    if "%" in _prediction:
                        _prediction = _prediction.strip("%")
                    else:
                        _prediction = str(float(_prediction) * 100)
                # 结果是纯数值
                gold = float(gold)
                match = re.search(r"([-+]?[0-9,.]+)(%)?", _prediction)
                if match:
                    number = match.group(1)  # 数值部分
                    percent_sign = match.group(2)  # 有百分号
                    if percent_sign:
                        number = float(number) / 100.0
                    else:
                        number = float(number)
                    if self.is_close_rel(gold, number):
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


if __name__ == "__main__":
    _data_list = load_finqa_data()
    evaObj = MultiHerttEvaluate()
    total_metrics = {
        "em": 0.0,
        "f1": 0.0,
        "answer_similarity": 0.0,
        "processNum": 0,
    }
    debug_index = None
    start_index = 0
    error_question_map = {"error": [], "no_answer": [], "system_error": []}
    for i, _item in enumerate(_data_list):
        if i < start_index:
            continue
        if debug_index is not None:
            if i != debug_index:
                continue
        _question = _item["qa"]["question"]
        _gold = str(_item["qa"]["exe_ans"])
        try:
            build_finqa_graph(_item)
            _prediction = qa(question=_question)
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
                error_question_map["system_error"].append(i)
            elif "i don't know" in _prediction.lower():
                error_question_map["no_answer"].append(i)
            else:
                error_question_map["error"].append(i)

        total_metrics["em"] += metrics["em"]
        total_metrics["f1"] += metrics["f1"]
        total_metrics["answer_similarity"] += metrics["answer_similarity"]
        total_metrics["processNum"] += 1

        print(total_metrics)
        print("error index list=" + str(error_question_map))
        print("#" * 100)
        if debug_index is not None:
            break
        if i >= 200:
            break
