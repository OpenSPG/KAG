import os
import csv


def extract_admin_types(input_file, output_file):
    """
    从指定的txt文件中提取行政区及其类型信息，并生成CSV文件
    提取类型包含"行政区"的条目以及对应的ID

    参数:
        input_file: 输入文本文件的路径
        output_file: 输出CSV文件的路径
    """
    # 存储行政区及其类型的字典
    admin_types = []
    # 存储行政区名称和对应ID的映射
    admin_id_map = {}

    # 处理单个文件
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

        # 首先提取所有ID映射
        for line in lines:
            parts = line.strip().split("\t")
            if len(parts) >= 3 and parts[1] == "label":
                admin_id = parts[0]
                admin_name = parts[2]
                admin_id_map[admin_name] = admin_id

        # 然后提取行政区类型信息
        for line in lines:
            parts = line.strip().split("\t")
            # 只提取类型中包含"行政区"的条目
            if len(parts) >= 3 and parts[1] == "type" and "行政区" in parts[2]:
                admin_name = parts[0]
                admin_type = parts[2]
                admin_id = admin_id_map.get(admin_name, "")  # 获取对应的ID，如果没有则为空字符串

                admin_types.append(
                    {
                        "行政区名称": admin_name,
                        "行政区类型": admin_type,
                        "行政区ID": admin_id,
                    }
                )

    # 写入CSV文件
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["行政区名称", "行政区类型", "行政区ID"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for item in admin_types:
            writer.writerow(item)

    print(f"已提取 {len(admin_types)} 个行政区类型信息并保存到 {output_file}")


if __name__ == "__main__":
    # 设置输入文件和输出文件路径
    dir = os.path.dirname(__file__)
    input_file = os.path.join(dir, "ZJ.txt")
    output_csv = os.path.join(dir, "行政区.csv")

    extract_admin_types(input_file, output_csv)
