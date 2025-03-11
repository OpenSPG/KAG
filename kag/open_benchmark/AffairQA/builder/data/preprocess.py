import pandas as pd
from collections import defaultdict
import os


def parse_txt_file(file_path):
    data_dict = defaultdict(lambda: defaultdict(dict))
    current_name = None
    current_type = None

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split("\t")
            if len(parts) < 3:
                continue

            name, key, value = parts[0], parts[1], parts[2]

            if key == "type":
                current_name = name
                current_type = value
                data_dict[current_type][current_name] = {"姓名": current_name}

            if current_name and current_type:
                data_dict[current_type][current_name][key] = value

    return data_dict


# 将数据写入 CSV
def save_to_csv(data_dict):
    for type_, entries in data_dict.items():
        records = list(entries.values())
        df = pd.DataFrame(records)
        filename = os.path.join(f"{os.path.dirname(__file__)}", f"{type_}.csv")
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"已保存: {filename}")


# 运行解析与保存

file_path = os.path.join(os.path.dirname(__file__), "ZJ.txt")  # 替换为你的文件路径
data_dict = parse_txt_file(file_path)
save_to_csv(data_dict)
