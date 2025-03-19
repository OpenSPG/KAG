def to_snake_case(name):
    import re

    words = re.findall("SQL|VBA|[A-Za-z][a-z0-9]*", name)
    result = "_".join(words).lower()
    return result


def main():
    import io
    import os
    import json

    dir_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(dir_path, "cs.jsonl")
    if not os.path.isfile(file_path):
        print(
            "Please download cs.jsonl from https://huggingface.co/datasets/TommyChien/UltraDomain/tree/main"
        )
        return
    with io.open(file_path, "r", encoding="utf-8", newline="\n") as fin:
        questions = []
        documents = set()
        for line in fin:
            item = json.loads(line)
            title = item["meta"]["title"]
            content = title + "\n" + item["context"]
            if content not in documents:
                name = to_snake_case(title)
                output_file_path = os.path.join(
                    dir_path, "builder", "data", name + ".md"
                )
                with io.open(
                    output_file_path, "w", encoding="utf-8", newline="\n"
                ) as fout:
                    print(content, file=fout)
            item["context"] = title
            questions.append(item)
        output_file_path = os.path.join(dir_path, "solver", "data", "questions.json")
        with io.open(output_file_path, "w", encoding="utf-8", newline="\n") as fout:
            json.dump(
                questions, fout, separators=(",", ": "), indent=4, ensure_ascii=False
            )
            print(file=fout)


if __name__ == "__main__":
    main()
