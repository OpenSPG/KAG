import os
import json
import asyncio

from kag.examples.bird_graph.solver.cypher.cypher_execute_engine import (
    CypherExecuteEngine,
)
from kag.common.registry import import_modules_from_path
from kag.examples.bird_graph.solver.qa import BirdQA


def get_eval_dataset(db_name):
    current_path = os.path.dirname(os.path.abspath(__file__))
    dataset_json = os.path.join(
        current_path,
        "..",
        "table_2_graph",
        "bird_dev_table_dataset",
        "dev_with_answer.json",
    )
    rst_list = []
    with open(dataset_json, "r", encoding="utf-8") as f:
        for line in f:
            dev_data = json.loads(line.strip())
            if dev_data["db_id"] != db_name:
                continue
            rst_list.append(dev_data)
    rst_list.sort(key=lambda x: x["question_id"])
    return rst_list


async def check_cypher(i, cypher, dev_data, query):
    rows, error_info = await CypherExecuteEngine().async_run(cypher, 9999)
    answer = dev_data["result"]
    print_rows = rows[:3]
    print_rows = list_to_set(print_rows)
    print_answer = answer[:3]
    print(
        f"index:{i}\nquestion:\n{query}\ncypher:\n{cypher}\nSQL:\n{dev_data['SQL']}\nresult:{len(rows)}\n{print_rows}\nanswer:{len(answer)}\n{print_answer}"
    )
    return compare_2d_arrays(rows, answer)


def is_hashable(obj):
    try:
        hash(obj)
        return True
    except TypeError:
        return False


def list_to_set(_list):
    n_list = []
    for item in _list:
        try:
            # convert item 2 float
            float_item = float(item)
            # round
            item = round(float_item, 2)
        except (ValueError, TypeError):
            pass
        if not is_hashable(item):
            item = str(item)
        n_list.append(item)
    return frozenset(n_list)


def list_to_str(_list):
    s = ""
    for item in _list:
        try:
            float_item = float(item)
            item = round(float_item, 2)
        except (ValueError, TypeError):
            pass
        s += str(item)
    return s


def compare_2d_arrays(arr1, arr2):
    set1 = {list_to_set(sublist) for sublist in arr1}
    set2 = {list_to_set(sublist) for sublist in arr2}

    # diff 2 sets
    return set1 == set2


async def qa_and_check(i, evaObj, query, db_name, test_data):
    cypher = await evaObj.qa(query=query, db_name=db_name)
    return await check_cypher(i, cypher, test_data, query)


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    import_modules_from_path("./component")

    db_name = "california_schools"
    evaObj = BirdQA()
    loop = asyncio.get_event_loop()
    _count = 0
    match_index = []
    debug_index = None
    for i, test_data in enumerate(get_eval_dataset(db_name)):
        if debug_index is not None and i != debug_index:
            continue
        query = test_data["question"]
        if test_data["evidence"]:
            query += f" evidence: {test_data['evidence']}"
        if i + 1 == 26:
            print("------")
        match = loop.run_until_complete(
            qa_and_check(i, evaObj, query, db_name, test_data)
        )
        if match:
            _count += 1
            match_index.append(i)
        print("#" * 100)
        print(f"process={i + 1},match={_count},p={_count / (i + 1)}")
        print("#" * 100)

    print("#" * 100)
    print(f"match_index={match_index}")
    print("#" * 100)
