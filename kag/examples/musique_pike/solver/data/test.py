import json
import random

def sample_json(input_file, output_file, sample_size):
    try:
        # 读取输入的 JSON 文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查数据是否是列表
        if not isinstance(data, list):
            raise ValueError("JSON 文件的根元素不是列表")

        # 确定采样数量
        sample_size = min(sample_size, len(data))  # 防止采样数超过列表长度

        # 随机采样
        sampled_data = random.sample(data, sample_size)

        # 保存到新的 JSON 文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sampled_data, f, ensure_ascii=False, indent=4)

        print(f"随机采样的 {sample_size} 条数据已保存到 {output_file}")

    except Exception as e:
        print(f"出现错误: {e}")

# 参数配置
input_file = '/Users/laven/Desktop/常识知识图谱/源代码/Semantic_KAG/KAG/dep/KAG/kag/examples/musique_pike/solver/data/musique_qa.json'  # 输入文件路径
output_file = '/Users/laven/Desktop/常识知识图谱/源代码/Semantic_KAG/KAG/dep/KAG/kag/examples/musique_pike/solver/data/musique_qa_dev.json'  # 输出文件路径
sample_size = 500  # 需要采样的记录数量

# 运行采样程序
sample_json(input_file, output_file, sample_size)