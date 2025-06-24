# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

import json
import logging
import os
import time
from typing import List
from kag.interface import LLMClient
from kag.common.benchmarks.evaluate import Evaluate
from kag.examples.utils import delay_run
from kag.open_benchmark.utils.eval_qa import EvalQa, running_paras, do_main
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.interface import SolverPipelineABC
from kag.solver.reporter.trace_log_reporter import TraceLogReporter

logger = logging.getLogger(__name__)


class EvaForNetOperatorQA(EvalQa):
    """
    init for kag client
    """

    def __init__(self, solver_pipeline_name="kag_solver_pipeline"):
        super().__init__(
            task_name="NetOperatorQA", solver_pipeline_name=solver_pipeline_name
        )

    async def qa(self, query, gold, **kwargs):
        reporter: TraceLogReporter = TraceLogReporter()
        retrieved_chunks = []

        pipeline = SolverPipelineABC.from_config(
            KAG_CONFIG.all_config[self.solver_pipeline_name]
        )
        answer = await pipeline.ainvoke(
            query,
            reporter=reporter,
            gold=gold,
            retrieved_chunks=retrieved_chunks,
            **kwargs,
        )

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")

        info, status = reporter.generate_report_data()
        return answer, {
            "info": info.to_dict(),
            "status": status,
            "retrieved_chunks": retrieved_chunks,
        }

    async def async_process_sample(self, data):
        sample_idx, sample, ckpt = data
        question = sample["question"]
        gold = sample["answer"]
        try:
            if ckpt and question in ckpt:
                print(f"found existing answer to question: {question}")
                prediction, trace_log = ckpt.read_from_ckpt(question)
            else:
                prediction, trace_log = await self.qa(
                    query=question, gold=gold, ckpt=ckpt
                )
                if ckpt:
                    ckpt.write_to_ckpt(question, (prediction, trace_log))
            metrics = self.do_metrics_eval([question], [prediction], [gold])
            metrics["recall"] = self.do_recall_eval(sample, [prediction], trace_log)
            return sample_idx, prediction, metrics, trace_log
        except Exception as e:
            import traceback

            logger.warning(
                f"process sample failed with error:{traceback.print_exc()}\nfor: {sample['question']} {e}"
            )
            return None

    def load_data(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def do_metrics_eval(
        self, questionList: List[str], predictions: List[str], golds: List[str]
    ):
        eva_obj = Evaluate()
        return eva_obj.getBenchMark(questionList, predictions, golds)

    def do_recall_eval(self, sample, references, trace_log):
        eva_obj = Evaluate()
        predictions = trace_log.get("retrieved_chunks", None)
        goldlist = []
        for s in sample["supporting_facts"]:
            goldlist.extend(s[1:])
        goldlist = sample["supporting_facts"][0][1:]
        return eva_obj.recall_top(
            predictionlist=predictions,
            goldlist=goldlist,
            is_chunk_data=False,
            fuzzy_mode="chinese_only",
        )


if __name__ == "__main__":
    import_modules_from_path("./src")
    delay_run(hours=0)
    # Parse command-line arguments
    parser = running_paras()
    args = parser.parse_args()
    qa_file_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), f"{args.qa_file or 'data/qa.json'}"
    )
    start = time.time()
    do_main(
        qa_file_path=qa_file_path,
        thread_num=args.thread_num,
        upper_limit=args.upper_limit,
        collect_file=args.res_file,
        eval_obj=EvaForNetOperatorQA(),
    )
    end = time.time()
    token_meter = LLMClient.get_token_meter()
    stat = token_meter.to_dict()

    logger.info(
        f"\n\nbenchmark successfully for {qa_file_path}\n\nTimes cost:{end-start}s\n\nTokens cost: {stat}"
    )
