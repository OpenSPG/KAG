import os
import re
import csv


def process_library_data(input_file, output_file=None, output_format="tsv"):
    """
    处理图书馆数据，将"属性 年份-值"的格式转换为"年份属性 值"
    并将每个图书馆的所有属性合并为一行输出

    参数:
    input_file (str): 输入文件路径
    output_file (str): 输出文件路径，如果为None则覆盖原文件
    output_format (str): 输出格式，'tsv'或'csv'
    """
    if output_file is None:
        output_file = input_file + ".temp"

    # 读取文件
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 存储所有图书馆信息的字典
    libraries = {}
    current_library = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split("\t")

        # 检测是否为图书馆实体的开始
        if len(parts) >= 3 and parts[1] == "type" and parts[2] == "图书馆":
            current_library = parts[0]
            # 初始化图书馆条目
            if current_library not in libraries:
                libraries[current_library] = {"id": current_library, "type": "图书馆"}
            continue

        # 如果不是图书馆数据，跳过
        if current_library is None or len(parts) < 3:
            continue

        entity, attribute, value = parts

        # 确认我们仍在处理同一个图书馆
        if entity != current_library:
            current_library = None if "type" in parts[1] else current_library
            continue

        # 检查值是否包含年份格式 (如 "2018年-一级馆")
        year_match = re.match(r"^(\d{4}年)-(.+)$", value)
        if year_match:
            year = year_match.group(1)  # 例如 "2018年"
            actual_value = year_match.group(2)  # 例如 "一级馆"

            # 创建新的属性和值
            new_attribute = year + attribute
            libraries[current_library][new_attribute] = actual_value
        else:
            # 不需要处理的行直接添加到图书馆属性
            libraries[current_library][attribute] = value

    # 写入处理后的数据
    if output_format == "csv":
        with open(output_file, "w", encoding="utf-8", newline="") as f:
            # 获取所有可能的属性名称
            all_attributes = set()
            for lib_data in libraries.values():
                all_attributes.update(lib_data.keys())

            # 排序属性，确保id和type在前面
            attributes = ["id", "type"]
            for attr in sorted(all_attributes):
                if attr not in attributes:
                    attributes.append(attr)

            writer = csv.DictWriter(f, fieldnames=attributes)
            writer.writeheader()
            writer.writerows(libraries.values())
    else:  # tsv格式
        with open(output_file, "w", encoding="utf-8") as f:
            # 获取所有可能的属性名称
            all_attributes = set()
            for lib_data in libraries.values():
                all_attributes.update(lib_data.keys())

            # 排序属性，确保id和type在前面
            attributes = ["id", "type"]
            for attr in sorted(all_attributes):
                if attr not in attributes:
                    attributes.append(attr)

            # 写入表头
            f.write("\t".join(attributes) + "\n")

            # 写入每个图书馆的数据
            for lib_data in libraries.values():
                row = [lib_data.get(attr, "") for attr in attributes]
                f.write("\t".join(row) + "\n")

    # 如果输出文件是临时文件，则替换原文件
    if output_file == input_file + ".temp":
        os.replace(output_file, input_file)
        print(f"已处理并覆盖原文件: {input_file} (格式: {output_format})")
    else:
        print(f"已处理并保存到: {output_file} (格式: {output_format})")


if __name__ == "__main__":
    # 用法示例
    import argparse

    dir_path = os.path.dirname(__file__)
    input_file = os.path.join(dir_path, "ZJ.txt")
    output_file = os.path.join(dir_path, "图书馆.csv")
    parser = argparse.ArgumentParser(description="处理图书馆数据")
    parser.add_argument("--input_file", default=input_file, help="输入文件路径")
    parser.add_argument("-o", "--output", default=output_file, help="输出文件路径，默认覆盖原文件")
    parser.add_argument(
        "-f",
        "--format",
        choices=["tsv", "csv"],
        default="csv",
        help="输出格式 (tsv 或 csv)，默认为 tsv",
    )

    args = parser.parse_args()

    process_library_data(args.input_file, args.output, args.format)
