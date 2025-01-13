import time
import numpy as np


def delay_run(hours: int):
    start_time = time.time()
    diff_time = time.time() - start_time
    while diff_time < hours * 3600:
        time.sleep(2)
        diff_time = time.time() - start_time
        print(f"diff_time: {diff_time}")


def compute_hit_in_recalls(recall_headers: list, supporting_facts: list, topk=3):
    if len(recall_headers) > topk:
        recall_headers = recall_headers[:topk]
    set1 = set(recall_headers)
    set2 = set(supporting_facts)
    inter = set1 & set2
    return len(inter) * 1.0 / len(supporting_facts)


def compute_sub_query(trace_log: dict):
    round_max_sub_query = 0
    kg_direct_num = 0
    sub_query_num = 0
    round_max_sub_query += 0 if len(trace_log) == 0 else len(trace_log[0]["history"])
    for log in trace_log:
        if "history" not in log:
            continue
        history = log["history"]

        for h in history:
            sub_query_num += 1
            source_type = h.get("answer_source", "chunk")
            if source_type == "spo":
                kg_direct_num += 1
    return kg_direct_num, sub_query_num, round_max_sub_query


def min_max_normalize(x):
    if np.max(x) - np.min(x) > 0:
        return (x - np.min(x)) / (np.max(x) - np.min(x))
    else:
        return x - np.min(x)


def run_rerank_by_score(recall_docs: list):
    recall_score_dict = {}
    for iter_recall_docs in recall_docs:
        tmp_dict = {}
        for doc in iter_recall_docs:
            score = doc.split("#")[-1]
            header = doc.replace(f"#{score}", "")
            tmp_dict[header] = score
        normalized_iter_doc_scores = min_max_normalize(
            np.array(list(tmp_dict.values())).astype(float)
        )
        normalized_tmp_dict = dict(zip(tmp_dict.keys(), normalized_iter_doc_scores))
        for header, score in normalized_tmp_dict.items():
            if header not in recall_score_dict:
                recall_score_dict[header] = score
            elif header in recall_score_dict and score > recall_score_dict[header]:
                recall_score_dict[header] = score
    sorted_recall_docs = sorted(
        recall_score_dict.items(), key=lambda item: item[1], reverse=True
    )
    return [f"{content}#{score}" for content, score in sorted_recall_docs]


def compute_recall_metrics(recall_docs: list, supporting_facts: list, extract_content):
    supporting_facts = list(set(supporting_facts))
    recall_docs_header = []
    for doc in recall_docs:
        header = extract_content(doc)
        if header is None:
            raise Exception(f"doc header extra failed {doc}")
        recall_docs_header.append(header)
    return (
        compute_hit_in_recalls(recall_docs_header, supporting_facts, 2),
        compute_hit_in_recalls(recall_docs_header, supporting_facts, 5),
        compute_hit_in_recalls(recall_docs_header, supporting_facts, 10),
        compute_hit_in_recalls(recall_docs_header, supporting_facts, 10000),
    )
