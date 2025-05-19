import io
import json

def main():
    file_path = "2wiki_res_1747368034.3445568.json"
    checked_file_path = "2wiki_res_1747368034.3445568_checked.json"
    with io.open(file_path, "r", encoding="utf-8") as fin:
        samples = json.load(fin)
    print("total samples:", len(samples))

    llm_filter_failed = 0
    llm_filter_success = 0
    llm_filter_over = 0
    llm_filter_missed = 0
    for sample in samples:
        is_supporting = set(x[0] for x in sample["supporting_facts"])
        if sample["traceLog"]["info"]["tag"] == "LLM_FILTER_FAILED":
            llm_filter_failed += 1
        elif sample["traceLog"]["info"]["tag"] == "LLM_FILTER_SUCCESS":
            llm_filter_success += 1
            llm_filtered = set(x["title"] for x in sample["traceLog"]["info"]["filtered_supporting_facts"])
            if llm_filtered != is_supporting:
                if llm_filtered - is_supporting != set():
                    llm_filter_over += 1
                    sample["traceLog"]["info"]["llm_filter_over"] = True
                if is_supporting - llm_filtered != set():
                    llm_filter_missed += 1
                    sample["traceLog"]["info"]["llm_filter_missed"] = True
        else:
            assert False, "invalid traceLog info tag"
    print("llm_filter_failed:", llm_filter_failed)
    print("llm_filter_success:", llm_filter_success)
    print("llm_filter_over:", llm_filter_over)
    print("llm_filter_missed:", llm_filter_missed)

    with io.open(checked_file_path, "w", encoding="utf-8", newline="\n") as fout:
        json.dump(samples, fout, separators=(",", ": "), indent=4, ensure_ascii=False)
        print(file=fout)

if __name__ == "__main__":
    main()
