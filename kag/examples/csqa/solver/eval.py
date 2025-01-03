class CsQaEvaluator(object):
    def __init__(self):
        self._questions = self._load_questions()

    def _load_questions(self):
        import io
        import os
        import json

        dir_path = os.path.dirname(os.path.abspath(__file__))
        dir_path = os.path.join(dir_path, "data")
        file_path = os.path.join(dir_path, "questions.json")
        with io.open(file_path, "r", encoding="utf-8", newline="\n") as fin:
            questions = json.load(fin)
        return questions

    def _save_answers(self):
        import io
        import os
        import json

        dir_path = os.path.dirname(os.path.abspath(__file__))
        dir_path = os.path.join(dir_path, "data")
        file_path = os.path.join(dir_path, "csqa_kag_answers.json")
        with io.open(file_path, "w", encoding="utf-8", newline="\n") as fout:
            json.dump(
                self._questions,
                fout,
                separators=(",", ": "),
                indent=4,
                ensure_ascii=False,
            )
            print(file=fout)

    def _get_question_answer(self, item):
        from kag.common.conf import KAG_CONFIG
        from kag.solver.logic.solver_pipeline import SolverPipeline

        resp = SolverPipeline.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])
        answer, trace_log = resp.run(item["input"])

        print(f"\n\nso the answer for '{item['input']}' is: {answer}\n\n")
        return answer, trace_log

    def _process_sample(self, index, item, ckpt):
        try:
            question = item["input"]
            if question in ckpt:
                print(f"found existing answer to question: {question}")
                answer, trace_log = ckpt.read_from_ckpt(question)
            else:
                answer, trace_log = self._get_question_answer(item)
                ckpt.write_to_ckpt(question, (answer, trace_log))
            item["kag_answer"] = answer
            item["kag_trace_log"] = trace_log
            return True
        except Exception:
            import traceback

            message = f"process question {index}. {item['input']} failed with exception:\n{traceback.format_exc()}"
            print(message)
            return False

    def _parallel_qa(self, thread_num=50):
        import time
        from tqdm import tqdm
        from concurrent.futures import ThreadPoolExecutor
        from concurrent.futures import as_completed
        from kag.common.checkpointer import CheckpointerManager

        ckpt = CheckpointerManager.get_checkpointer(
            {"type": "zodb", "ckpt_dir": "ckpt"}
        )
        start = time.monotonic_ns()
        with ThreadPoolExecutor(max_workers=thread_num) as executor:
            futures = [
                executor.submit(self._process_sample, index, item, ckpt)
                for index, item in enumerate(self._questions, 1)
            ]
            processed = 0
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="parallel qa: ",
            ):
                result = future.result()
                if result:
                    processed += 1
        delta = (time.monotonic_ns() - start) / 1e9
        print("Processed %d questions." % processed)
        print("Elapsed time: %.2f seconds" % delta)
        CheckpointerManager.close()

    def run(self):
        self._parallel_qa()
        self._save_answers()


def main():
    import os
    from kag.common.registry import import_modules_from_path

    dir_path = os.path.dirname(os.path.abspath(__file__))
    import_modules_from_path(dir_path)

    evaluator = CsQaEvaluator()
    evaluator.run()


if __name__ == "__main__":
    main()
