import os
import json
import asyncio

from neo4j import GraphDatabase

from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path

from kag.examples.bird_graph.solver.qa import BirdQA

from neo4j.exceptions import Neo4jError


def get_eval_dataset():
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
            if dev_data["db_id"] != "california_schools":
                continue
            rst_list.append(dev_data)
    return rst_list


NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j@openspg"
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def check_cypher(cypher, dev_data):
    with driver.session(database="birdgraph") as session:
        try:
            result = session.run(cypher)
            records = [record for record in result]
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
        f"question:{dev_data['question']}\ncypher:\n{cypher}\nresult:\n{print_rows}\nanswer:\n{print_answer}"
    )
    return compare_2d_arrays(rows, answer)


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
        s += f",{item}"
    return s[1:]  # 去掉开头多余的逗号


def compare_2d_arrays(arr1, arr2):

    # 对每个二维数组的第一维进行排序并转换为集合
    set1 = {list_to_str(sublist) for sublist in arr1}
    set2 = {list_to_str(sublist) for sublist in arr2}

    # 比较两个集合是否相等
    return set1 == set2


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    import_modules_from_path("./component")

    evaObj = BirdQA()
    loop = asyncio.get_event_loop()
    _count = 0
    for i, test_data in enumerate(get_eval_dataset()):
        query = test_data["question"]
        if test_data["evidence"]:
            query += f" evidence: {test_data['evidence']}"
        cypher = loop.run_until_complete(evaObj.qa(query=query))
        match = check_cypher(cypher, test_data)
        if match:
            _count += 1
        print("#" * 100)
        print(f"process={i+1},match={_count},p={_count/(i+1)}")
        print("#" * 100)
