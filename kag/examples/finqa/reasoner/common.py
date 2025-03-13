from kag.interface.solver.base_model import LFPlan


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
