from kag.interface.solver.base_model import LFPlan

from kag.interface.solver.base_model import LFExecuteResult

from enum import Enum


class ExecuteStatus(Enum):
    NO_RECALL = 1


def get_all_recall_docs(execute_rst_list: list[LFExecuteResult], rerank_doc=True):
    _recall_docs = []
    for _, exe_info in enumerate(execute_rst_list):
        docs = exe_info.recall_docs
        if rerank_doc:
            docs = exe_info.rerank_docs
        if len(docs) <= 0:
            continue
        _recall_docs.extend(docs)
    return _norm_doc_retrieved(_recall_docs)


def get_execute_context(
    question, execute_rst_list: list[LFExecuteResult], with_code: bool = False
) -> list:
    context_list = []
    if len(execute_rst_list) <= 0:
        return context_list

    # 子问题和answer map
    sub_qa_map = {}
    docs_map = {}
    doc_index = 0
    for _, exe_info in enumerate(execute_rst_list):
        exe_info: LFExecuteResult = exe_info
        docs = exe_info.rerank_docs
        docs = _norm_doc_retrieved(docs)
        for doc in docs:
            if doc not in docs_map:
                doc_index += 1
                docs_map[doc] = doc_index

        query = "\n".join([lf_plan.query for lf_plan in exe_info.sub_plans])
        sub_qa_map[query] = docs

    if len(sub_qa_map) <= 0:
        context_list.append((question, "retrival", None, None))
        return context_list

    in_context_docs_map = {}
    for q, docs in sub_qa_map.items():
        answer = ""
        if len(docs) <= 0:
            answer = "No relevant documents found"
            context_list.append((q, "retrival", answer, None))
            continue
        for doc in docs:
            if doc in in_context_docs_map:
                doc_index = in_context_docs_map[doc]
                doc = f"[Reference](Documnt {doc_index})"
            else:
                doc_index = docs_map[doc]
                in_context_docs_map[doc] = doc_index
                doc = f"### [Documnt {doc_index}]\n```\n{doc}\n```"
            if len(answer) > 0:
                answer += "\n"
            answer += doc
        context_list.append((q, "retrival", answer, None))

    for _, exe_info in enumerate(execute_rst_list):
        exe_info: LFExecuteResult = exe_info
        for _, lf_plan in enumerate(exe_info.sub_plans):
            lf_plan: LFPlan = lf_plan
            if lf_plan.sub_query_type != "math":
                continue
            answer = f"The result of Python execution is: {lf_plan.res.sub_answer}"
            if with_code:
                python_code = lf_plan.res.debug_info["code"]
                answer = f"Python code is:\n```python{python_code}```\nExecution result: {lf_plan.res.sub_answer}"
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
        context_str += f"\nSubQuestion{i+1}({c[1]}): {c[0]}\nResult{i+1}:\n{c[2]}\n"
    return context_str


def _norm_doc(doc):
    _doc: str = doc
    _doc = _doc.strip("#")
    x = _doc.rfind("#")
    try:
        is_float = False
        float(_doc[x + 1 :])
        is_float = True
    except:
        pass
    if is_float:
        _doc = _doc[:x]
    x = _doc.find("#")
    if x > 0:
        _doc = _doc[x + 1 :]
    return _doc


def _norm_doc_retrieved(docs):
    rst_list = []
    for doc in docs:
        doc = _norm_doc(doc)
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
