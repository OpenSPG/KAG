# coding=utf-8
import json
import sys
import os
import numpy as np
import time
import re

# 错误字典，这里只是示例
error_msg={
    1: "Bad input file",
    2: "Wrong input file format",
}


def dump_2_json(info, path):
    with open(path, 'a+') as output_json_file:
        json.dump(info, output_json_file)
        output_json_file.write('\n')


def report_error_msg(detail, showMsg, out_p):
    error_dict=dict()
    error_dict['errorDetail']=detail
    error_dict['errorMsg']=showMsg
    error_dict['score']=0
    error_dict['scoreJson']={}
    error_dict['success']=False
    dump_2_json(error_dict,out_p)


def report_score(dataset,score, out_p):
    result = dict()
    result['dataset']=dataset
    result['success']=True
    result['score'] = score

    # 这里{}里面的score注意保留，但可以增加其他key，比如这样：
    # result['scoreJson'] = {'score': score, 'aaaa': 0.1}
    result['scoreJson'] = {'score': score}

    dump_2_json(result,out_p)


def calculate_precision_recall_f1(prediction, label):
    TP = len(set(prediction)&set(label))
    FP = len(set(prediction)-set(label))
    FN = len(set(label)-set(prediction))
    precision = TP / (TP + FP) if TP + FP != 0 else 0
    recall = TP / (TP + FN) if TP + FN != 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall != 0 else 0
    return precision, recall, f1


def is_digit_and_chinese(s):
    # 正则表达式匹配规则：开始位置有一个或多个数字，后面跟着一个或多个汉字，直到字符串结束
    pattern = r'^\d+\p{Script=Han}+$'
    if re.match(pattern, s):
        return True
    else:
        return False


def get_score(gold_answer, user_answer,dataset):
    gold = gold_answer[dataset]
    submit = user_answer[dataset]
    # 计算得分
    precision_list = []
    recall_list = []
    f1_list = []

    for k, v in gold.items():
        label = v
        if k in submit:
            prediction = submit[k]

            if label == ['没有'] or label == ['不是'] or label == ['否'] or label == ['无'] or label == ['不同'] or label == ['知识库未提及']: label = ['0']
            if prediction == ['没有'] or prediction == ['No'] or prediction == ['no'] or prediction == ['否'] or prediction == ['不属于'] or prediction == ['不是'] or prediction == ['不相同'] or prediction == ['No.'] or prediction == ['不同'] or prediction == ['无'] or prediction == ['知识库未提及']: prediction = ['0']

            # 处理 ["数字+单位"] 的情况, 例如 ["1个"]
            if re.match(r'(\d+).*', label[0])!= None and re.match(r'(\d+).*', prediction[0]) != None:
                label[0] = re.match(r'(\d+).*', label[0]).group(1)
                prediction[0] = re.match(r'(\d+).*', prediction[0]).group(1)

            precision, recall, f1 = calculate_precision_recall_f1(prediction, label)
        else:
            precision, recall, f1 = 0, 0, 0

        if f1 != 1:
            print("问题：", k)
            print("标准答案：", label)
            print("选手提交：", prediction)
        precision_list.append(precision)
        recall_list.append(recall)
        f1_list.append(f1)

    precision = np.mean(precision_list)
    recall = np.mean(recall_list)
    f1 = np.mean(f1_list)

    return f1


# python evaluator.py user_answer.json out.json
if __name__=="__main__":
    '''
        evaluation  
    '''
    base_dir = os.path.dirname(__file__)
    user_answer_path = os.path.join(base_dir, "solver/data/prediction_result.json")
    gold_answer_path = os.path.join(base_dir, "solver/data/gold_answer.json")
    out_path = os.path.join(base_dir, "solver/data/evaluation.json")

    # 标准答案路径
    with open(gold_answer_path, 'r') as load_f:
        gold = json.load(load_f)
    gold_answer = dict()

    for dataset_name, items in gold.items():
        answer_dict = dict()
        for item in items:
            answer_dict.update(item)
        gold_answer[dataset_name] = answer_dict
    print(f"Read standard from {gold_answer_path}")

    # 读取用户答案
    with open(user_answer_path, 'r') as load_f:
        user = json.load(load_f)
    user_answer = dict()

    for dataset_name, items in user.items():
        answer_dict = dict()
        for item in items:
            answer_dict.update(item)
        user_answer[dataset_name] = answer_dict
    print(f"Read user submit file from {user_answer_path}")

    f1_list = []
    dataset = "PeopleRelationshipsQA"
    try:
        score = get_score(gold_answer, user_answer, dataset)
        f1_list.append(score)
        report_score(dataset, score, out_path)
    except Exception as e:
        f1_list.append(0)
        # 错误类型
        error_type = type(e).__name__
        print("Error type:", error_type)
        # 错误信息
        error_msg = str(e)
        print("Error message:", error_msg)

        report_error_msg(error_type, error_msg, out_path)

    report_score("Average", sum(f1_list)/len(f1_list), out_path)