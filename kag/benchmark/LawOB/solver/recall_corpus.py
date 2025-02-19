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
#
# import json
# import os
# from concurrent.futures import as_completed, ThreadPoolExecutor
#
# from tqdm import tqdm
# from kag.common.checkpointer import CheckpointerManager
# from kag.common.conf import KAG_CONFIG
# from kag.common.registry import import_modules_from_path
# from kag.interface import KagBaseModule, LLMClient
# from kag.solver.logic.solver_pipeline import SolverPipeline
# from kag.solver.retriever.impl.default_chunk_retrieval import DefaultChunkRetriever
# from kag.solver.utils import init_prompt_with_fallback
#
# import_modules_from_path("./")
#
# class ExtraKeyWord(KagBaseModule):
#     """
#     Initializes the base planner.
#     """
#
#     def __init__(self, **kwargs):
#         llm_client = LLMClient.from_config(KAG_CONFIG.all_config['chat_llm'])
#         super().__init__(llm_client, **kwargs)
#         self.extra_search_key_prompt = init_prompt_with_fallback("extra_key_word", self.biz_scene)
#
#     def run(self, query):
#         return self.llm_module.invoke({'instruction': query}, self.extra_search_key_prompt, with_json_parse=False)
#
# def load_jsons_from_folder(folder_path):
#     # 创建一个空字典用于存放结果
#     result = {}
#
#     # 遍历给定文件夹下的所有文件
#     for filename in os.listdir(folder_path):
#         # 检查文件是否为.json文件
#         if filename.endswith('.json'):
#             # 构建完整的文件路径
#             file_path = os.path.join(folder_path, filename)
#
#             # 打开并读取json文件内容
#             with open(file_path, 'r', encoding='utf-8') as file:
#                 try:
#                     # 解析json数据
#                     data = json.load(file)
#                     # 使用文件名（去除.json后缀）作为key，将数据存入字典
#                     key = os.path.splitext(filename)[0]
#                     result[key] = data
#                 except json.JSONDecodeError:
#                     print(f"警告: 文件 {filename} 不是一个有效的JSON文件。")
#
#     return result
#
#
# total_curpos = {}
# process_file_dir = ["zero_shot"]
# extra_key_word = ExtraKeyWord()
#
# ckpt = CheckpointerManager.get_checkpointer(
#     {"type": "zodb", "ckpt_dir": "ckpt"}
# )
# for process_file in process_file_dir:
#     folder_path = f"data/{process_file}"
#     result = load_jsons_from_folder(folder_path)
#     for key, cases in result.items():
#         test_output = []
#
#         def process_one_v(t):
#             idx, value = t
#             cur_corpus = {}
#             answer = value['answer']
#             question = value['question']
#             key_words = extra_key_word.run(f"Q:{question}\nA:{answer}")
#             query = f"请根据下面内容召回对应支撑知识：{key_words}\n "
#             # if question in ckpt:
#             #     print(f"found existing answer to question: {question}")
#             #     answer, trace_log = ckpt.read_from_ckpt(question)
#             # else:
#             resp = SolverPipeline.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])
#             answer, trace_log = resp.run(query)
#                 # ckpt.write_to_ckpt(question, (answer, trace_log))
#             for doc in trace_log[0]['rerank docs']:
#                 title = doc.split('#')[1].strip()
#                 if title not in cur_corpus:
#                     cur_corpus[title] = [doc.replace(doc.split('#')[1], '')]
#                 else:
#                     if doc.replace(doc.split('#')[1], '') not in cur_corpus[title]:
#                         cur_corpus[title].append(doc.replace(doc.split('#')[1], ''))
#             return idx, cur_corpus
#
#
#         process_one_v((0, {
#             "instruction": "请你模拟法官依据下面事实给出罪名，只需要给出罪名的名称，将答案写在[罪名]和<eoa>之间。例如[罪名]盗窃;诈骗<eoa>。请你严格按照这个格式回答。",
#             "question": "事实:经审理查明，2014年1月30日，河南欧某乳业生物科技有限公司（以下简称欧某公司）与被告人陈某签订的销售合作协议到期，并于同年1月31日起停止生产广东长荣实业投资有限公司的旺仔复合蛋白饮品。2014年11月底的一天，陈某隐瞒上述事实，仍以欧某公司经销商的名义要求被害人李某1付款24160元用于购买欧某公司生产的旺仔复合蛋白饮品。2014年12月2日，陈某收到货款后一直未向李某1发货，并于2015年5月更换手机号致使李某1无法联络。\r\n案发后，被告人陈某已退还被害人全部赃款，并取得被害人的谅解。\r\n上述事实，被告人陈某在开庭审理过程中亦无异议，并有书证抓获经过、被告人户籍信息、银行交易明细及清单、河南省朴食堂食品有限公司出库单、经销合同、欧某湖北销售公司旺仔系列饮品价格表、商标使用许可合同、终止协议、销售合作协议、在逃人员信息表、旺仔牛奶样本照片、辨认笔录、退款收据及谅解书；证人刘某2、周某的证言；被害人李某1、李某2的陈述；被告人陈某的供述与辩解；武昌区司法局出具的社会调查表等证据证实，足以认定。\r\n",
#             "answer": "罪名:诈骗",
#         }))
#         with ThreadPoolExecutor(max_workers=1) as executor:
#             futures = [
#                 executor.submit(process_one_v, (sample_idx, sample))
#                 for sample_idx, sample in enumerate(cases)
#             ]
#             for future in tqdm(
#                     as_completed(futures),
#                     total=len(futures),
#                     desc="parallelQaAndEvaluate completing: ",
#             ):
#                 result = future.result()
#                 idx = result[0]
#                 cur_corpus = result[1]
#                 for title, passages in cur_corpus.items():
#                     if title not in total_curpos:
#                         total_curpos[title] = passages
#                     else:
#                         for passage in passages:
#                             if passage not in total_curpos[title]:
#                                 total_curpos[title].append(passage)
#                 value = cases[idx]
#                 value['context'] = cur_corpus
#                 test_output.append(value)
#                 if idx > 0 and idx%5 == 0:
#                     with open(f"./data/output/{process_file}/{key}_case_test.json", "w") as f:
#                         json.dump(test_output, f, indent=2, ensure_ascii=False)
#     with open(f"./data/output/law_corpus.json", "w") as f:
#         json.dump(total_curpos, f, indent=2, ensure_ascii=False)
