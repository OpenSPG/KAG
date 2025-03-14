from kag.interface.solver.base_model import LFPlan

from kag.interface.solver.base_model import LFExecuteResult

from enum import Enum


class ExecuteStatus(Enum):
    NO_RECALL = 1


def _norm_doc_retrieved2(docs):
    rst_list = []
    for doc in docs:
        doc: str = doc
        doc = doc.strip("#")
        x = doc.find("#")
        if x > 0:
            doc = doc[x + 1 :]
        rst_list.append(doc.strip())
    return rst_list


def get_all_recall_docs(execute_rst_list: list[LFExecuteResult], rerank_doc=True):
    _recall_docs = []
    for _, exe_info in enumerate(execute_rst_list):
        docs = exe_info.recall_docs
        if rerank_doc:
            docs = exe_info.rerank_docs
        if len(docs) <= 0:
            continue
        _recall_docs.extend(docs)
    return _norm_doc_retrieved2(_recall_docs)


def get_execute_context(question, execute_rst_list: list[LFExecuteResult]) -> list:
    context_list = []
    if len(execute_rst_list) <= 0:
        return context_list
    _all_recall_docs = get_all_recall_docs(execute_rst_list)
    if len(_all_recall_docs) <= 0:
        context_list.append((question, "retrival", None, None))
        return context_list

    answer = "\n".join(_all_recall_docs)
    context_list.append((question, "retrival", answer, None))
    for _, exe_info in enumerate(execute_rst_list):
        exe_info: LFExecuteResult = exe_info
        for _, lf_plan in enumerate(exe_info.sub_plans):
            lf_plan: LFPlan = lf_plan
            if lf_plan.sub_query_type != "math":
                continue
            answer = (
                f"The result calculated by the calculator is: {lf_plan.res.sub_answer}"
            )
            context_list.append(
                (lf_plan.query, lf_plan.sub_query_type, answer, lf_plan.res.debug_info)
            )
    return context_list


def get_history_context_info_list(history: list):
    doc_map = {}
    doc_index = 0
    context_list = []
    for _, lf_plan in enumerate(history):
        lf_plan: LFPlan = lf_plan
        if lf_plan.sub_query_type == "math":
            answer = (
                f"The result calculated by the calculator is: {lf_plan.res.sub_answer}"
            )
        else:
            if len(lf_plan.res.doc_retrieved) <= 0:
                doc_list = []
            else:
                doc_list = _norm_doc_retrieved(lf_plan.res.doc_retrieved)
            new_doc_list = []
            for doc in doc_list:
                if doc not in doc_map:
                    doc_index += 1
                    refer_index = doc_index
                    doc_map[doc] = refer_index
                    new_doc_list.append((doc, refer_index))
                else:
                    refer_index = doc_map[doc]
                    new_doc_list.append((None, refer_index))
            answer = _refer_doc_list_to_str(new_doc_list)
        context_list.append((lf_plan.query, lf_plan.sub_query_type, answer))
    return context_list


def get_history_context_str(context_list):
    if len(context_list) <= 0:
        return None
    context_str = ""
    for i, c in enumerate(context_list):
        context_str += f"\nSubQuestion{i+1}({c[1]}): {c[0]}\nResult{i+1}: {c[2]}\n"
    return context_str


def _norm_doc_retrieved(docs):
    rst_list = []
    for doc in docs:
        doc: str = doc
        doc = doc.strip("#")
        x = doc.rfind("#")
        doc = doc[:x]
        x = doc.find("#")
        if x > 0:
            doc = doc[x + 1 :]
        rst_list.append(doc.strip())
    return rst_list


def _refer_doc_list_to_str(docs):
    if len(docs) <= 0:
        return "No results retrieved."
    rst_str = ""
    for doc, refer_index in docs:
        if doc is None:
            rst_str += f"\n[Reference](Document {refer_index})"
        else:
            rst_str += f"\n[Document {refer_index}]: {doc}"
    return rst_str
