import os
import re
import json

from kag.examples.finqa.dyna_shot.error_log import ERROR_LIST_0317_1, ERROR_LIST_0317_2


from kag.interface import LLMClient

from kag.common.conf import KAG_CONFIG


from kag.solver.utils import init_prompt_with_fallback

from kag.examples.finqa.dyna_shot.failure_analysis_prompt import (
    FinQAFalureAnalysisPrompt,
)


def load_finqa_data(_type="test") -> list:
    """
    load data
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = os.path.join(current_dir, "..", "builder", "data", f"{_type}.json")
    with open(file_name, "r", encoding="utf-8") as f:
        data_list = json.load(f)
    print("finqa data list len " + str(len(data_list)))
    for _idx, data in enumerate(data_list):
        data["index"] = _idx
    print(f"type={_type},len={len(data_list)}")
    return data_list


def get_gold_inds_from_data_set(item):
    pass


def get_answer_from_log(log: str):
    pass


def get_answer_map(index_set):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file = os.path.join(current_dir, "..", "solver", "nohup.out")
    with open(file, "r", encoding="utf-8") as f:
        conetnt = f.read()
    return parse_answer_log(conetnt, index_set)


def parse_answer_log(log: str, index_set):
    answer_map = {}
    pattern = r"finqa_processing_log\ni=(\d+)\nid=(.*?)\n<\|memory\|>(.*?)<\|memory\|>\n<\|code\|>(.*?)<\|code\|>"
    matches = re.findall(pattern, log, re.DOTALL)
    for match in matches:
        i, id, memory, code = match
        i = int(i)
        if i not in index_set:
            continue
        answer_map[i] = (memory.strip(), code.strip())
    pattern = f"##########\nindex=(\d+),gold=(.*?),prediction=(.*?)\n"
    matches = re.findall(pattern, log, re.DOTALL)
    for match in matches:
        i, gold, prediction = match
        i = int(i)
        if i not in index_set:
            continue
        if i not in answer_map:
            continue
        memory, code = answer_map[i]
        answer_map[i] = (memory, code, gold, prediction)
    return answer_map


if __name__ == "__main__":
    min_index = 770
    max_index = 981
    error_set1 = set()
    for i, _ in ERROR_LIST_0317_1["error"]:
        if i > max_index:
            continue
        error_set1.add(i)
    for i, _ in ERROR_LIST_0317_1["system_error"]:
        if i > max_index:
            continue
        error_set1.add(i)
    error_set2 = set()
    for i, _ in ERROR_LIST_0317_2["error"]:
        if i > max_index:
            continue
        error_set2.add(i)
    for i, _ in ERROR_LIST_0317_2["system_error"]:
        if i > max_index:
            continue
        error_set2.add(i)
    diff1 = error_set1 - error_set2
    diff2 = error_set2 - error_set1
    intersect = error_set1.intersection(error_set2)

    # check diff first
    failed_index_set = diff1.union(diff2)
    # check intersection，基本都是题目错误
    # failed_index_set = intersect
    answer_map = get_answer_map(failed_index_set)
    gold_map = {}
    data_list = load_finqa_data()
    for data in data_list:
        data_index = data["index"]
        if data_index not in failed_index_set:
            continue
        if data_index < min_index:
            continue
        question = data["qa"]["question"]
        gold_inds = str(data["qa"]["gold_inds"])
        program_re = str(data["qa"]["program_re"])
        answer = str(data["qa"]["answer"])
        gold_map[data_index] = (question, gold_inds, program_re, answer)

    llm_client: LLMClient = LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])
    falure_analysis_prompt = init_prompt_with_fallback("falure_analysis", "finqa")

    for i, v in gold_map.items():
        if i not in answer_map:
            continue
        question, gold_inds, program_re, answer = v
        memory, code, gold, prediction = answer_map[i]
        params = {
            "question": question,
            "gold_inds": gold_inds,
            "program_re": program_re,
            "memory": memory,
            "code": code,
            "gold": gold,
            "prediction": prediction,
        }
        print("#" * 100)
        print(
            f"index={i}\nquestion:{question}\ngold:{gold},answer:{answer},prediction:{prediction}\ngold_inds:{gold_inds}\nprogram:{program_re}\nmemory:{memory}\n\ncode:\n{code}"
        )
        # response = llm_client.invoke(
        #     variables=params,
        #     prompt_op=falure_analysis_prompt,
        #     with_json_parse=False,
        #     with_except=True,
        # )
        # print("#" * 100)
        # print(response)
        print("#" * 100)
