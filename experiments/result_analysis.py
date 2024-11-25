#!/usr/bin/python
# encoding: utf-8
"""
Project: openspgapp
Auther: Zhongpu Bo
Email: zhongpubo.bzp@antgroup.com
DateTime: 2024/10/30 11:55
Description: 

"""

import json

from itertools import chain


def load_result(result_file):
    raw_json = json.load(open(result_file, 'r'))
    pred_dict = {}
    for item in raw_json:
        key = item.get("_id") or item["id"]
        if "traceLog" not in item:
            print("skip invalid item.")
            continue
        if "supporting_facts" not in item:
            _sf = []
            for par in item["paragraphs"]:
                if par["is_supporting"]:
                    _sf.append([par["title"], 0])
            item["supporting_facts"] = _sf

        if 'context' in item:
            context_dict = {k: v for k, v in item["context"]}
            ref_docs = [context_dict[s][ix if ix < len(context_dict[s]) else 0] for s, ix in item["supporting_facts"]]
        else:
            context_dict = {}
            for par in item["paragraphs"]:
                if par["is_supporting"]:
                    context_dict.setdefault(par["title"], []).append(par["paragraph_text"])
            ref_docs = [context_dict[s] for s, ix in item["supporting_facts"]]

        if '"history":' in item:
            ans_source_type = list(chain(*[[h['answer_source'] for h in trace['history']] for trace in item["traceLog"]]))
            infer_path = list(chain(
                *[[h['sub_query'] + '###' + h['sub_answer'] for h in trace['history']] for trace in item["traceLog"]]
            ))
        else:
            ans_source_type, infer_path, pred_docs = [], [], {}

        pred_docs = [d.strip('#').split('#')[0].split('\n')[0] for d in item["traceLog"][-1]["rerank_docs"]]
        pred_docs = [d[7:] if d.startswith('Title: ') else d for d in pred_docs]

        pred_dict[key] = {
            "question": item["question"],
            "answer": item["answer"],
            "pred": item["prediction"],
            "gold_docs": [i[0] for i in item["supporting_facts"]],
            "pred_docs": pred_docs,
            "answer_source": ans_source_type,
            "em": item["em"],
            "f1": item["f1"],
            "reference": ref_docs,
            "infer_path": infer_path,
        }

    return pred_dict


def chunk_recall(result_dict, k_list=None):
    k_list = k_list if k_list else [1, 2, 5, 10]
    ranks = []
    n_cases = 0
    n_gold = 0
    for item in list(result_dict.values()):
        pred = item["pred_docs"]
        if not pred:  # 非chunk retrieval
            continue
        gold = item["gold_docs"]
        n_cases += 1
        n_gold += len(gold)
        for true in gold:
            rank = pred.index(true) if true in pred else 100
            ranks.append(rank)
    res = {}
    for k in k_list:
        res[f"Recall@{k}"] = sum([r < k for r in ranks]) / n_gold

    print(json.dumps(res, ensure_ascii=False, indent=4))
    return res


if __name__ == '__main__':

    dataset = '2wiki'  # 2wiki hotpotqa

    target_file = f"/knext/experiments/results/hotpotqa_ircot_hippo_res.json"  #{dataset}_deepseek_LF_SRC_res.json"
    pred = load_result(target_file)
    chunk_recall(pred)
