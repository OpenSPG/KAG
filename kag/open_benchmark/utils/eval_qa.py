import argparse
import asyncio
import logging
import time

import aiofiles
import json
from typing import List

from tqdm import tqdm
from kag.common.conf import KAG_CONFIG
from kag.interface import SolverPipelineABC

from kag.common.checkpointer import CheckpointerManager
from kag.solver.reporter.trace_log_reporter import TraceLogReporter

logger = logging.getLogger(__name__)


class EvalQa:
    def __init__(self, task_name, solver_pipeline_name):
        self.solver_pipeline_name = solver_pipeline_name
        self.task_name = task_name

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
                print(f"processing answer to question: {question}")
                prediction, trace_log = await self.qa(query=question, gold=gold)
                if ckpt:
                    ckpt.write_to_ckpt(question, (prediction, trace_log))

            metrics = await asyncio.to_thread(
                lambda: self.do_metrics_eval([question], [prediction], [gold])
            )
            gold_aliases = sample.get("answer_aliases", [])

            def compare_metrics(metrics1, metrics2):
                ret_metrics = {}
                for key in metrics1:
                    ret_metrics[key] = (
                        metrics1[key]
                        if metrics2[key] < metrics1[key]
                        else metrics2[key]
                    )
                return ret_metrics

            for gold_alias in gold_aliases:
                updated_metrics = await asyncio.to_thread(
                    lambda: self.do_metrics_eval([question], [prediction], [gold_alias])
                )
                metrics = compare_metrics(metrics, updated_metrics)

            recall_metrics = self.do_recall_eval(
                sample, trace_log["info"].get("reference", [])
            )
            metrics.update(recall_metrics)
            return sample_idx, prediction, metrics, trace_log
        except Exception as e:
            import traceback

            logger.warning(
                f"process sample failed with error:{traceback.print_exc()}\nfor: {sample['question']} {e}"
            )
            return None

    def do_metrics_eval(
        self, questionList: List[str], predictions: List[str], golds: List[str]
    ):
        raise NotImplementedError("do_eval need implement")

    def do_recall_eval(self, sample, references):
        return {"recall": None}

    def do_total_metrics_process(self, metrics_list: List[dict]):
        total_metrics = {
            "processNum": len(metrics_list),
        }
        if len(metrics_list) == 0:
            return total_metrics
        res_metrics = {}
        for metric in metrics_list:
            for k, v in metric.items():
                if not isinstance(v, int) and not isinstance(v, float):
                    continue
                if k not in total_metrics:
                    total_metrics[k] = 0.0
                total_metrics[k] += v
        for k, v in total_metrics.items():
            if k in ["processNum"]:
                res_metrics[k] = v
            else:
                res_metrics[k] = v * 1.0 / len(metrics_list)
        return res_metrics

    async def parallel_qa_and_evaluate(
        self, qa_list, res_file_path, thread_num=1, upper_limit=10
    ):
        ckpt = CheckpointerManager.get_checkpointer(
            {"type": "zodb", "ckpt_dir": "ckpt"}
        )
        res_qa = []
        semaphore = asyncio.Semaphore(thread_num)  # 控制并发度

        async def bounded_process_sample(data):
            async with semaphore:
                return await self.async_process_sample(data)

        tasks = [
            asyncio.create_task(bounded_process_sample((sample_idx, sample, ckpt)))
            for sample_idx, sample in enumerate(qa_list[:upper_limit])
        ]
        metrics_list = []
        for task in tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc=f"parallelQaAndEvaluate {self.task_name} completing: ",
        ):
            result = await task
            if result is not None:
                sample_idx, prediction, metrics, traceLog = result
                sample = qa_list[sample_idx]

                sample["prediction"] = prediction
                sample["traceLog"] = traceLog
                sample["metrics"] = metrics
                metrics_list.append(metrics)
                res_qa.append(sample)

                if sample_idx % 20 == 0:
                    await self.async_write_json(res_file_path, res_qa)
        await self.async_write_json(res_file_path, res_qa)

        return res_qa, metrics_list

    async def async_write_json(self, file_path, data):
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data))

    def load_data(self, file_path):
        """
        need write how to load test case,format like that
        [
            {
                "question": "xxxx",
                "answer": "yyy"
            }
        ]
        """
        raise NotImplementedError("load_data need implement")

    def eval_main(self, file_path, thread_num, upper_limit):
        start_time = time.time()
        result_metrics_file_path = f"{self.task_name}_metrics_{start_time}.json"
        result_test_file_path = f"{self.task_name}_res_{start_time}.json"
        qa_list = self.load_data(file_path)
        qa_list_res, metrics_list = asyncio.run(
            self.parallel_qa_and_evaluate(
                qa_list,
                result_test_file_path,
                thread_num=thread_num,
                upper_limit=upper_limit,
            )
        )
        total_metrics = self.do_total_metrics_process(metrics_list)
        total_metrics["cost"] = time.time() - start_time
        total_metrics["task_name"] = self.task_name
        with open(result_metrics_file_path, "w") as f:
            json.dump(total_metrics, f)
        print(total_metrics)
        return total_metrics


def do_main(qa_file_path, thread_num, upper_limit, eval_obj, collect_file=None):
    result = eval_obj.eval_main(qa_file_path, thread_num, upper_limit)
    metrics_lines = ""
    for key, value in result.items():
        metrics_lines += f"{key}: {value}\t"
    print(metrics_lines)
    if collect_file:
        with open(collect_file, "a") as f:
            f.writelines("\n" + metrics_lines)


def running_paras():
    parser = argparse.ArgumentParser(description="qa args")
    # 添加参数
    parser.add_argument("--qa_file", type=str, help="test file name in /data")
    parser.add_argument("--thread_num", type=int, help="thread num to run", default=10)
    parser.add_argument("--upper_limit", type=int, help="upper limit", default=1000)
    parser.add_argument(
        "--res_file", type=str, help="record store file", default="benchmark.txt"
    )
    return parser
