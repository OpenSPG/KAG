import json


def count_correct(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "details" in data:
        # 如果数据在details字段中
        evaluation_list = data["details"]
    else:
        # 如果数据直接是列表
        evaluation_list = data

    total = len(evaluation_list)
    correct = sum(1 for item in evaluation_list if "正确" in item["evaluation"][:10])

    print(f"总样本数: {total}")
    print(f"正确数量: {correct}")
    print(f"正确率: {correct/total*100:.2f}%")


# 使用文件路径
count_correct("./evaluation_results_4.json")
