import json
import os
import requests
from typing import List, Dict
import yaml
import jieba
from collections import Counter
import concurrent.futures
from tqdm import tqdm


def load_config(config_path: str) -> Dict:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def normalize_answer(s: str) -> List[str]:
    """对答案进行标准化处理，包括分词"""
    # 移除多余空格和换行符
    s = " ".join(s.split())
    # 使用结巴分词
    return [token for token in jieba.cut(s) if token.strip()]


def compute_exact_match(pred_tokens: List[str], answer_tokens: List[str]) -> float:
    """计算EM分数"""
    return float(pred_tokens == answer_tokens)


def compute_f1(pred_tokens: List[str], answer_tokens: List[str]) -> float:
    """计算F1分数"""
    common = Counter(pred_tokens) & Counter(answer_tokens)
    num_same = sum(common.values())

    if len(pred_tokens) == 0 or len(answer_tokens) == 0:
        return 0

    precision = num_same / len(pred_tokens)
    recall = num_same / len(answer_tokens)

    if precision + recall == 0:
        return 0

    f1 = 2 * precision * recall / (precision + recall)
    return f1


def extract_answer_from_prediction(prediction: str) -> str:
    """从预测文本中提取答案部分"""
    # 直接返回整个预测文本
    return prediction.strip()


def evaluate_qa(qa_file: str):
    # 固定配置
    api_key = os.getenv("BAILIAN_API_KEY")
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/"
    model = "qwen-max-latest"

    # 读取QA数据
    with open(qa_file, "r", encoding="utf-8") as f:
        qa_data = json.load(f)

    total_em = 0
    total_f1 = 0
    results = []

    # 定义处理单个QA项的函数
    def process_qa_item(item):
        # 处理标准答案（可能是列表）
        if isinstance(item["answer"], list):
            standard_answer = item["answer"][0]  # 取第一个答案
        else:
            standard_answer = item["answer"]

        # 检查是否存在prediction字段
        if "prediction" not in item:
            print(f"警告: ID为{item.get('id', '未知')}的数据缺少prediction字段")
            return None

        # 从预测中提取答案部分
        predicted_answer = extract_answer_from_prediction(item["prediction"])

        # 标准化答案
        standard_tokens = normalize_answer(standard_answer)
        predicted_tokens = normalize_answer(predicted_answer)

        # 计算EM和F1分数
        em_score = compute_exact_match(predicted_tokens, standard_tokens)
        f1_score = compute_f1(predicted_tokens, standard_tokens)

        # 构建提示词进行正确性评估
        prompt = f"""请评估以下问答对的正确性：

问题：{item['question']}
标准答案：{standard_answer}
模型预测：{predicted_answer}

请判断模型预测是否与标准答案一致。只需回答"正确"或"错误"，并简要说明理由。"""

        # 调用大模型评估
        try:
            evaluation = call_llm(api_key, base_url, model, prompt)
        except Exception as e:
            evaluation = f"API调用失败: {str(e)}"

        # 返回结果
        return {
            "id": item["id"],
            "question": item["question"],
            "standard_answer": standard_answer,
            "prediction": predicted_answer,
            "evaluation": evaluation,
            "em_score": em_score,
            "f1_score": f1_score,
        }

    # 使用线程池并发处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # 提交所有任务并显示进度条
        future_to_item = {
            executor.submit(process_qa_item, item): item for item in qa_data
        }

        # 使用tqdm显示进度
        for future in tqdm(
            concurrent.futures.as_completed(future_to_item),
            total=len(qa_data),
            desc="评估进度",
        ):
            result = future.result()
            if result:
                results.append(result)
                total_em += result["em_score"]
                total_f1 += result["f1_score"]

    # 计算平均分数
    avg_em = total_em / len(qa_data)
    avg_f1 = total_f1 / len(qa_data)

    # 添加总体评估结果
    final_results = {"average_em": avg_em, "average_f1": avg_f1, "details": results}

    # 保存评估结果
    output_file = f"evaluation_results_{qa_file.split('/')[-1].split('.')[0][-1]}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)

    print(f"评估完成！结果已保存至 {output_file}")
    print(f"平均EM分数: {avg_em:.4f}")
    print(f"平均F1分数: {avg_f1:.4f}")


def call_llm(api_key: str, base_url: str, model: str, prompt: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    response = requests.post(f"{base_url}chat/completions", headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    dir_path = os.path.dirname(__file__)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--qa_file", type=str, default="solver/data/res14.json")
    args = parser.parse_args()
    qa_file = os.path.join(dir_path, args.qa_file)
    evaluate_qa(qa_file)
