import json
import logging
import os
import time
from typing import List
from kag.interface import LLMClient
from kag.common.registry import Functor
from kag.common.benchmarks.evaluate import Evaluate
from kag.examples.utils import delay_run
from kag.open_benchmark.utils.eval_qa import EvalQa, running_paras, do_main
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.interface import SolverPipelineABC
from kag.solver.reporter.trace_log_reporter import TraceLogReporter

logger = logging.getLogger(__name__)


class EvaFor2wiki(EvalQa):
    """
    init for kag client
    """

    def __init__(self, solver_pipeline_name="kag_solver_pipeline"):
        super().__init__(task_name="2wiki", solver_pipeline_name=solver_pipeline_name)

    async def qa(self, query, gold):
        reporter: TraceLogReporter = TraceLogReporter()

        pipeline = SolverPipelineABC.from_config(
            KAG_CONFIG.all_config[self.solver_pipeline_name]
        )
        answer = await pipeline.ainvoke(query, reporter=reporter, gold=gold)

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")

        info, status = reporter.generate_report_data()
        return answer, {"info": info.to_dict(), "status": status}

    async def async_process_sample(self, data):
        sample_idx, sample, ckpt = data
        question = sample["question"]
        gold = sample["answer"]
        try:
            if ckpt and question in ckpt:
                print(f"found existing answer to question: {question}")
                prediction, trace_log = ckpt.read_from_ckpt(question)
            else:
                prediction, trace_log = await self.qa(query=question, gold=gold)
                if ckpt:
                    ckpt.write_to_ckpt(question, (prediction, trace_log))
            metrics = self.do_metrics_eval([question], [prediction], [gold])
            return sample_idx, prediction, metrics, trace_log
        except Exception as e:
            import traceback

            logger.warning(
                f"process sample failed with error:{traceback.print_exc()}\nfor: {sample['question']} {e}"
            )
            return None

    def load_data(self, file_path):
        with open(file_path, "r") as f:
            return json.load(f)

    def do_metrics_eval(
        self, questionList: List[str], predictions: List[str], golds: List[str]
    ):
        eva_obj = Evaluate()
        return eva_obj.getBenchMark(questionList, predictions, golds)


@Functor.register("benchmark_solver_2wiki")
def eval(qa_file_path, thread_num=10, upper_limit=1000, collect_file="benchmark.txt"):
    eval_obj = EvaFor2wiki()
    start = time.time()
    metric = do_main(
        qa_file_path=qa_file_path,
        thread_num=thread_num,
        upper_limit=upper_limit,
        collect_file=collect_file,
        eval_obj=eval_obj,
    )
    end = time.time()
    token_meter = LLMClient.get_token_meter()
    stat = token_meter.to_dict()

    logger.info(
        f"\n\nbenchmark successfully for {qa_file_path}\n\nTimes cost:{end-start}s\n\nTokens cost: {stat}"
    )
    return {"time_cost": end - start, "token_cost": stat, "metric": metric}


if __name__ == "__main__":
    import_modules_from_path("./src")
    delay_run(hours=0)
    # 解析命令行参数
    parser = running_paras()
    args = parser.parse_args()
    qa_file_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), f"{args.qa_file}"
    )
    start = time.time()
    do_main(
        qa_file_path=qa_file_path,
        thread_num=args.thread_num,
        upper_limit=args.upper_limit,
        collect_file=args.res_file,
        eval_obj=EvaFor2wiki(),
    )
    end = time.time()
    token_meter = LLMClient.get_token_meter()
    stat = token_meter.to_dict()

    logger.info(
        f"\n\nbenchmark successfully for {qa_file_path}\n\nTimes cost:{end-start}s\n\nTokens cost: {stat}"
    )
