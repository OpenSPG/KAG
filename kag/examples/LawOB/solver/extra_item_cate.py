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
import re
from concurrent.futures import as_completed, ThreadPoolExecutor

from knext.reasoner.rest.models.reason_task import ReasonTask
from tqdm import tqdm

from build.lib.knext.reasoner.client import ReasonerClient
from kag.common.checkpointer import CheckpointerManager
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.interface import KagBaseModule, LLMClient
from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.solver.retriever.impl.default_chunk_retrieval import DefaultChunkRetriever
from kag.solver.utils import init_prompt_with_fallback
from knext.search.client import SearchClient

from concurrent.futures import ThreadPoolExecutor, as_completed


def convert_chinese_to_arabic(chinese_number):
    # 定义中文数字到阿拉伯数字的映射
    chinese_numbers = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000
    }

    # 将中文数字字符串分割成各个部分
    parts = []
    i = 0
    while i < len(chinese_number):
        if i + 1 < len(chinese_number) and chinese_number[i:i + 2] in chinese_numbers:
            parts.append(chinese_numbers[chinese_number[i:i + 2]])
            i += 2
        else:
            parts.append(chinese_numbers[chinese_number[i]])
            i += 1

    # 计算总和
    total = 0
    temp = 0
    for part in parts:
        if part >= 10:
            if temp == 0:
                temp = 1
            temp *= part
        else:
            temp += part
        if temp >= 10:
            total += temp
            temp = 0
    total += temp

    return total

def convert_arabic_to_chinese(arabic_number):
    # 定义阿拉伯数字到中文数字的映射
    arabic_to_chinese = {
        0: '零', 1: '一', 2: '二', 3: '三', 4: '四',
        5: '五', 6: '六', 7: '七', 8: '八', 9: '九'
    }

    # 处理特殊情况
    if arabic_number == 10:
        return '十'
    elif arabic_number < 10:
        return arabic_to_chinese[arabic_number]

    # 分解数字
    parts = []
    if arabic_number >= 1000:
        parts.append(f'{arabic_to_chinese[arabic_number // 1000]}千')
        arabic_number %= 1000
    if arabic_number >= 100:
        parts.append(f'{arabic_to_chinese[arabic_number // 100]}百')
        arabic_number %= 100
    if arabic_number >= 10:
        if arabic_number % 10 == 0:
            parts.append('十')
        else:
            parts.append(f'{arabic_to_chinese[arabic_number // 10]}十')
        arabic_number %= 10
    if arabic_number > 0:
        parts.append(arabic_to_chinese[arabic_number])

    return ''.join(parts)


def extract_and_convert_clause(text):
    # 正则表达式匹配“第...条”
    pattern = r'第(.*?)条'

    # 查找所有匹配项
    matches = re.findall(pattern, text)

    results = []
    for match in matches:
        if match.isdigit():
            # 如果是阿拉伯数字
            arabic_number = int(match)
            chinese_number = convert_arabic_to_chinese(arabic_number)
            results.append((f"第{chinese_number}条", f"第{arabic_number}条"))
        else:
            # 如果是中文数字
            arabic_number = convert_chinese_to_arabic(match)
            results.append((f"第{match}条", f"第{arabic_number}条"))

    return results


def run():
    law_mapping = {
        "中华人民共和国劳动争议仲裁调解法": "中华人民共和国劳动争议调解仲裁法",
        "中华人民共和国工伤保险条例": "工伤保险条例",
        "中华人民共和国社会保险法若干规定": "中华人民共和国社会保险法"
    }
    law_name_item = {}
    # load graph
    with open("./data/item_law_with_name.jsonl", "r") as f:
        for line in f.readlines():
            law_items = json.loads(line)
            law_name= ""
            law_item_name = ""
            num_index = []
            for node in law_items['resultNodes']:
                if node['label'] == 'LegalName':
                    law_name = node["id"]
                if node['label'] == 'LegalItem':
                    law_item_name = node["id"]
                if node['label'] == "ItemIndex":
                    num_index.append(node["id"])

            law_name = law_name.replace(" ", "")
            law_name = law_name.replace("、", "")
            law_name = law_name.replace("《", "").replace("》", "")
            law_name = law_name.replace("<", "").replace(">", "")

            if law_name in law_name_item.keys():
                for i in num_index:
                    law_name_item[law_name].append([law_item_name, i])
            else:
                law_name_item[law_name] = []
                for i in num_index:
                    law_name_item[law_name].append([law_item_name, i])
            """
            {
	"resultNodes": [{
		"id": "人民检察院刑事诉讼规则",
		"name": "人民检察院刑事诉讼规则",
		"label": "LegalName",
		"properties": {}
	}, {
		"id": "人民检察院刑事诉讼规则第三百六十五条",
		"name": "人民检察院刑事诉讼规则第三百六十五条",
		"label": "LegalItem",
		"properties": {
			"name": "人民检察院刑事诉讼规则第三百六十五条",
			"content": "人民检察院刑事诉讼规则 第三百六十五条 --  人民检察院对于监察机关或者公安机关移送起诉的案件，发现犯罪嫌疑人没有犯罪事实，或者符合刑事诉讼法第十六条规定的情形之一的，经检察长批准，应当作出不起诉决定。对于犯罪事实并非犯罪嫌疑人所为，需要重新调查或者侦查的，应当在作出不起诉决定后书面说明理由，将案卷材料退回监察机关或者公安机关并建议重新调查或者侦查。"
		}
	}, {
		"id": "第三百六十五条",
		"name": "第三百六十五条",
		"label": "ItemIndex",
		"properties": {}
	}, {
		"id": "第365条",
		"name": "第365条",
		"label": "ItemIndex",
		"properties": {}
	}],
	"resultEdges": [{
		"id": 13211328464,
		"from": "人民检察院刑事诉讼规则第三百六十五条",
		"to": "人民检察院刑事诉讼规则",
		"fromType": "LegalItem",
		"toType": "LegalName",
		"label": "belongtolaw",
		"properties": {}
	}, {
		"id": 13211361344,
		"from": "人民检察院刑事诉讼规则第三百六十五条",
		"to": "第三百六十五条",
		"fromType": "LegalItem",
		"toType": "ItemIndex",
		"label": "belongtoitem",
		"properties": {}
	}, {
		"id": 13211361392,
		"from": "人民检察院刑事诉讼规则第三百六十五条",
		"to": "第365条",
		"fromType": "LegalItem",
		"toType": "ItemIndex",
		"label": "belongtoitem",
		"properties": {}
	}]
}
            """

    import_modules_from_path("./")

    class ExtraItemWord(KagBaseModule):
        """
        Initializes the base planner.
        """

        def __init__(self, **kwargs):
            llm_client = LLMClient.from_config(KAG_CONFIG.all_config['chat_llm'])
            super().__init__(llm_client, **kwargs)
            self.extra_search_key_prompt = init_prompt_with_fallback("extra_item_word", self.biz_scene)

        def run(self, query):
            return self.llm_module.invoke({'instruction': query}, self.extra_search_key_prompt, with_json_parse=False)
    extra_key_word = ExtraItemWord()
    search_client =SearchClient(host_addr="http://127.0.0.1:8887", project_id=1)
    reasoner_client = ReasonerClient(host_addr="http://127.0.0.1:8887", project_id=1)
    with open("/Users/peilong/Downloads/zero_shot/3-8_case_test_mark_with_item.json", "r") as f:
        test_cases = json.load(f)
        def process_data(sample):
            sample_idx = sample[0]
            value = sample[1]
            answer = value['answer']
            question = value['question']
            key_words = value['item']
            # key_words = extra_key_word.run(f"Q:{question}\nA:{answer}")
            # value['item'] = key_words
            value['context'] = []
            support_facts = []
            for item in key_words.split(","):
                item = item.replace(" ", "")
                item = item.replace("、", "")
                item = item.replace("《", "").replace("》", "")
                item = item.replace("<", "").replace(">", "")
                num = extract_and_convert_clause(item)
                law_name = item.replace(num[-1][0], "")
                law_name = law_name.replace(num[-1][1], "")
                if law_name in law_mapping.keys():
                    law_name = law_mapping[law_name]
                if law_name == "最高人民法院关于人民法院民事执行中查封扣押冻结财产的规定":
                    print(law_name)
                def get_legal_name_list(legal_name):
                    contans_item = []
                    for k in law_name_item.keys():
                        if legal_name == k:
                            return law_name_item[k]
                        if legal_name in k:
                            contans_item.append(k)
                    if len(contans_item) == 1:
                        return law_name_item[contans_item[0]]
                    print(f"{legal_name} same {contans_item}")
                    return None
                law_res = get_legal_name_list(law_name)
                if law_res:
                    cur_support_facts = []
                    for i in law_res:
                        if i[1] == num[-1][1] or i[1] == num[-1][0]:
                            cur_support_facts.append(i[0])
                            break
                    if cur_support_facts:
                        support_facts += cur_support_facts
                        continue
                else:
                    print(f"{sample_idx}: warn  {item} not found : law item ={law_name}")
            value['support_facts'] = support_facts
            return value
        updated_ele = []
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = [
                executor.submit(process_data, (sample_idx, sample))
                for sample_idx, sample in enumerate(test_cases)
            ]
            for future in tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc="parallelQaAndEvaluate completing: ",
            ):
                value = future.result()
                updated_ele.append(value)


    with open("/Users/peilong/Downloads/zero_shot/3-8_case_test_mark_with_item_res.json", "w") as f:
        json.dump(updated_ele, f, indent=2, ensure_ascii=False)

run()