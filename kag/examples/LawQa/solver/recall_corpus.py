""""
corpus format
{
    "chunk title": "chunk content"
}


test format

[
    {
        "supporting_facts": [
            [
                "Christopher Nolan",
                0
            ]
        ],
        "level": "medium",
        "question": "Are Christopher Nolan and Sathish Kalathil both film directors?",
        "context": [
            [
                "Christopher Nolan",
                [
                    "Christopher Edward Nolan ( ; born 30 July 1970) is an English-American film director, producer, and screenwriter.",
                    " He is one of the highest-grossing directors in history, and among the most successful and acclaimed filmmakers of the 21st century."
                ]
            ],
        ],
        "answer": "yes",
        "_id": "5ae40c465542996836b02c25",
        "type": "comparison"
    }
]
"""
import json
import os
from concurrent.futures import as_completed, ThreadPoolExecutor

from tqdm import tqdm
from kag.common.checkpointer import CheckpointerManager
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.interface import KagBaseModule, LLMClient
from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.solver.retriever.impl.default_chunk_retrieval import DefaultChunkRetriever
from kag.solver.utils import init_prompt_with_fallback

import_modules_from_path("./prompt")

class ExtraKeyWord(KagBaseModule):
    """
    Initializes the base planner.
    """

    def __init__(self, **kwargs):
        llm_client = LLMClient.from_config(KAG_CONFIG.all_config['chat_llm'])
        super().__init__(llm_client, **kwargs)
        self.extra_search_key_prompt = init_prompt_with_fallback("extra_key_word", self.biz_scene)

    def run(self, query):
        return self.llm_module.invoke({'instruction': query}, self.extra_search_key_prompt, with_json_parse=False)

def load_jsons_from_folder(folder_path):
    # 创建一个空字典用于存放结果
    result = {}

    # 遍历给定文件夹下的所有文件
    for filename in os.listdir(folder_path):
        # 检查文件是否为.json文件
        if filename.endswith('.json'):
            # 构建完整的文件路径
            file_path = os.path.join(folder_path, filename)

            # 打开并读取json文件内容
            with open(file_path, 'r', encoding='utf-8') as file:
                try:
                    # 解析json数据
                    data = json.load(file)
                    # 使用文件名（去除.json后缀）作为key，将数据存入字典
                    key = os.path.splitext(filename)[0]
                    result[key] = data
                except json.JSONDecodeError:
                    print(f"警告: 文件 {filename} 不是一个有效的JSON文件。")

    return result


total_curpos = {}
process_file_dir = ["zero_shot"]
extra_key_word = ExtraKeyWord()

ckpt = CheckpointerManager.get_checkpointer(
    {"type": "zodb", "ckpt_dir": "ckpt"}
)
for process_file in process_file_dir:
    folder_path = f"data/{process_file}"
    result = load_jsons_from_folder(folder_path)
    for key, cases in result.items():
        test_output = []
        def process_one_v(t):
            idx, value = t
            cur_corpus = {}
            answer = value['answer']
            question = value['question']
            key_words = extra_key_word.run(f"Q:{question}\nA:{answer}")
            query = f"请根据下面内容召回对应支撑的法律依据：{key_words}\n 依据:?"
            if question in ckpt:
                print(f"found existing answer to question: {question}")
                answer, trace_log = ckpt.read_from_ckpt(question)
            else:
                resp = SolverPipeline.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])
                answer, trace_log = resp.run(query)
                ckpt.write_to_ckpt(question, (answer, trace_log))
            for doc in trace_log[0]['rerank docs']:
                title = doc.split('#')[1].strip()
                if title not in cur_corpus:
                    cur_corpus[title] = [doc.replace(doc.split('#')[1], '')]
                else:
                    if doc.replace(doc.split('#')[1], '') not in cur_corpus[title]:
                        cur_corpus[title].append(doc.replace(doc.split('#')[1], ''))
            # ret = extra_key_word.llm_module.invoke({'instruction': query}, extra_key_word.extra_search_key_prompt, with_json_parse=False)
            # if ret is None or not isinstance(ret, str):
            #     query = answer
            # else:
            #     print(f"=====\n{ret} query={query}")
            #     query = ret
            # chunk_retriever.recall_docs()
            # def recall_by_vector(q):
            #     answer_vector = chunk_retriever.vectorizer.vectorize(q)
            #     top_k = chunk_retriever.sc.search_vector(
            #         label="Entity",
            #         property_key="content",
            #         query_vector=answer_vector,
            #         topk=10,
            #     )
            #     return top_k
            #
            # def recall_by_text(q):
            #     return chunk_retriever.sc.search_text(q, topk=10)
            #
            # recall_docs_set = recall_by_vector(query)
            # if len(recall_docs_set) == 0:
            #     recall_docs_set += recall_by_text(query)
            # for node in recall_docs_set:
            #     title = node['node']['name'].strip()
            #     content = node['node']['content'].strip()
            #     if title not in cur_corpus:
            #         cur_corpus[title] = [content]
            #     else:
            #         if content not in cur_corpus[title]:
            #             cur_corpus[title].append(content)
            return idx, cur_corpus

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(process_one_v, (sample_idx, sample))
                for sample_idx, sample in enumerate(cases)
            ]
            for future in tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc="parallelQaAndEvaluate completing: ",
            ):
                result = future.result()
                idx = result[0]
                cur_corpus = result[1]
                for title, passages in cur_corpus.items():
                    if title not in total_curpos:
                        total_curpos[title] = passages
                    else:
                        for passage in passages:
                            if passage not in total_curpos[title]:
                                total_curpos[title].append(passage)
                value = cases[idx]
                value['context'] = cur_corpus
                test_output.append(value)
                if idx > 0 and idx%5 == 0:
                    with open(f"./data/output/{process_file}/{key}_case_test.json", "w") as f:
                        json.dump(test_output, f, indent=2, ensure_ascii=False)
    with open(f"./data/output/law_corpus.json", "w") as f:
        json.dump(total_curpos, f, indent=2, ensure_ascii=False)
