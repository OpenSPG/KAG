import re
import pandas as pd
import json
from kag.common.benchmarks.evaluate import Evaluate

def parse_txt_to_excel(input_file, output_file):
    entries = []
    current_entry = {}
    current_field = None
    pattern = re.compile(r'^(id|query|answer|理由|trace_log)[：:]\s*(.*)')

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            match = pattern.match(line)

            if match:
                # 检查是否遇到了新的`id`字段，如果有，保存之前的条目
                if match.group(1) == 'id' and current_entry:
                    entries.append(current_entry)
                    current_entry = {}

                # 开始处理新的字段
                current_field = match.group(1)
                value = match.group(2)
                current_entry[current_field] = value.strip()
            else:
                # 追加非匹配行到当前字段的值
                if current_field:
                    current_entry[current_field] += ' ' + line

        # 添加最后一个条目
        if current_entry:
            entries.append(current_entry)

    # 处理可能缺失的字段并确保没有空格干扰
    for entry in entries:
        for field in ['id', 'query', 'answer', '理由', 'trace_log']:
            entry[field] = entry.get(field, '').strip()

    # 创建DataFrame并调整列顺序
    df = pd.DataFrame(entries)
    df = df[['id', 'query', 'answer', '理由', 'trace_log']]

    # 保存到Excel
    df.to_excel(output_file, index=False, engine='openpyxl')



def add_standard_answers_to_excel(excel_file, json_file, output_file):
    # 读取JSON文件并创建一个字典以便快速查找标准答案
    with open(json_file, 'r', encoding='utf-8') as f:
        gold_answers = json.load(f)

    # 创建一个字典，将id映射到其标准答案
    # answer_dict = {entry['id']: entry['answer'][0] for entry in gold_answers}
    answer_dict = {str(entry['id']).strip(): '、'.join(entry['answer']) for entry in gold_answers}

    # 读取Excel文件
    df = pd.read_excel(excel_file, engine='openpyxl')
    df['id'] = df['id'].astype(str).str.strip()
    # 创建一个新的列来存储标准答案
    df['standard_answer'] = df['id'].map(answer_dict)

    # 将DataFrame写回到Excel文件
    df.to_excel(output_file, index=False, engine='openpyxl')

if __name__ == "__main__":
    input_file = 'queries_output.txt'
    excel_file = 'output_query.xlsx'
    json_file = '/Users/wan/Documents/src/gold_answer/PeopleRelationshipsQA.json'
    output_file = 'output_with_standard_answers.xlsx'

    # parse_txt_to_excel(input_file, excel_file)
    # add_standard_answers_to_excel

    df = pd.read_excel(output_file, engine='openpyxl')
    query = df.iloc[:, 1]  # 第二列，使用索引从0开始
    prediction = df.iloc[:, 2]  # 第三列，使用索引从0开始
    gold = df.iloc[:, 5]  # 第六列，使用索引从0开始
    prediction = prediction.tolist()
    gold = gold.tolist()
    evalObj = Evaluate()
    # api_key = 'yerVkcSl95O19JG7n2dP6q2iNhSmdVmN'
    # base_url = 'https://antchat.alipay.com/v1/'
    # model = 'Bailing-4.0-80B-16K-Chat'
    total_metrics = evalObj.getSummarizationMetrics(query, prediction, gold,
                                                    api_key = "yerVkcSl95O19JG7n2dP6q2iNhSmdVmN",
                                                    base_url = "https://antchat.alipay.com/v1/",
                                                    model = "Bailing-4.0-80B-16K-Chat")
    print(total_metrics)