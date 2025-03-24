import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.solver.logic.solver_pipeline import SolverPipeline

logger = logging.getLogger(__name__)


def load_processed_ids(progress_file):
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()


def save_processed_id(id, progress_file):
    processed_ids = load_processed_ids(progress_file)
    processed_ids.add(id)
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(list(processed_ids), f)


def qa(query):
    resp = SolverPipeline.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])

    try:
        query_id = query.get("id")
        to_query = query.get("question")

        answer, trace_log = resp.run(to_query)
        print(f"\n\nso the answer for '{to_query}' is:\n {answer}\n\n")
        print(trace_log)
        return query_id, answer, trace_log
    except (ValueError, TypeError) as e:  # 捕获具体的异常
        import traceback
        logger.warning(
            f"process sample failed with known error: {e}\n{traceback.format_exc()}\n"
        )
        return None
    except Exception as e:  # 兜底捕获未知异常
        import traceback
        logger.error(
            f"process sample failed with unexpected error: {e}\n{traceback.format_exc()}\n"
        )
        return None


def execute_parallel_qa(qa_file_path, res_file_path, thread_num=1, upper_limit=10):
    with open(qa_file_path, "r") as f:
        qa_list = json.load(f)

    processed_count = 0  # 计数器
    with ThreadPoolExecutor(max_workers=thread_num) as executor:
        futures = [
            executor.submit(qa, query)
            for query_id, query in enumerate(qa_list[:upper_limit])
        ]
        for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="parallel Qa for PRQA completing: ",
        ):
            result = future.result()
            if result is not None:
                query_id, answer, trace_log = result
                query_id = int(query_id)
                sample = qa_list[query_id]
                sample["answer"] = answer
                sample["trace_log"] = trace_log

                processed_count += 1
                if processed_count % 2 == 0:
                    with open(res_file_path, "a", encoding="utf-8") as file:
                        json.dump(qa_list, file, ensure_ascii=False)

    with open(res_file_path, "a", encoding="utf-8") as file:
        json.dump(qa_list, file, ensure_ascii=False)


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    json_file_path = "./data/test.json"
    progress_file = "./progress21.json"

    execute_parallel_qa(json_file_path, progress_file, thread_num=5, upper_limit=202)

    # question = "《利箭纵横》的主要演员的哪位搭档与陈道明搭档过？"
    # qa_answer, traceLog = qa(question)
    # print(f"Question: {question}")
    # print(f"Answer: {qa_answer}")
    # print(f"TraceLog: {traceLog}")
