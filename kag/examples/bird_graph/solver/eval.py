import os
import json
import asyncio

from neo4j import GraphDatabase

from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path

from kag.examples.bird_graph.solver.qa import BirdQA

from neo4j import AsyncGraphDatabase
from neo4j.exceptions import Neo4jError


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
            # 解析每行 JSON 数据并添加到列表中
            dev_data = json.loads(line.strip())
            if dev_data["db_id"] != db_name:
                continue
            rst_list.append(dev_data)
    rst_list.sort(key=lambda x: x["question_id"])
    return rst_list


NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j@openspg"
driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


async def check_cypher(i, cypher, dev_data, query):
    async with driver.session(database="birdgraph") as session:
        try:
            result = await session.run(cypher)
            records = [record async for record in result]
        except (Neo4jError, ValueError) as e:
            print("cypher run error")
            records = [[]]

        # 获取查询结果
        rows = []
        for record in records:
            rows.append(list(record))
    answer = dev_data["result"]
    print_rows = rows[:3]
    print_answer = answer[:3]
    print(
        f"index:{i}\nquestion:\n{query}\ncypher:\n{cypher}\nSQL:\n{dev_data['SQL']}\nresult:{len(rows)}\n{print_rows}\nanswer:{len(answer)}\n{print_answer}"
    )
    return compare_2d_arrays(rows, answer)


def is_hashable(obj):
    try:
        hash(obj)  # 尝试计算 hash 值
        return True
    except TypeError:  # 如果对象不可哈希，会抛出 TypeError
        return False


def list_to_set(_list):
    n_list = []
    for item in _list:
        try:
            # 尝试将 item 转换为浮点数
            float_item = float(item)
            # 四舍五入到小数点后两位
            item = round(float_item, 2)
        except (ValueError, TypeError):
            # 如果转换失败（不是数字或无法转换），保持原样
            pass
        if not is_hashable(item):
            item = str(item)
        n_list.append(item)
    return frozenset(n_list)


def list_to_str(_list):
    s = ""
    for item in _list:
        try:
            # 尝试将 item 转换为浮点数
            float_item = float(item)
            # 四舍五入到小数点后两位
            item = round(float_item, 2)
        except (ValueError, TypeError):
            # 如果转换失败（不是数字或无法转换），保持原样
            pass
        s += str(item)
    return s


def compare_2d_arrays(arr1, arr2):

    # 对每个二维数组的第一维进行排序并转换为集合
    set1 = {list_to_set(sublist) for sublist in arr1}
    set2 = {list_to_set(sublist) for sublist in arr2}

    # 比较两个集合是否相等
    return set1 == set2


async def qa_and_check(i, evaObj, query, db_name, test_data):
    cypher = await evaObj.qa(query=query, db_name=db_name)
    match = await check_cypher(i, cypher, test_data, query)
    return match


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    import_modules_from_path("./component")

    db_name = "california_schools"
    evaObj = BirdQA()
    loop = asyncio.get_event_loop()
    _count = 0
    debug_index = None
    for i, test_data in enumerate(get_eval_dataset(db_name)):
        if debug_index is not None and i != debug_index:
            continue
        query = test_data["question"]
        if test_data["evidence"]:
            query += f" evidence: {test_data['evidence']}"
        match = loop.run_until_complete(qa_and_check(i, evaObj, query, db_name, test_data))
        if match:
            _count += 1
        print("#" * 100)
        print(f"process={i+1},match={_count},p={_count/(i+1)}")
        print("#" * 100)
