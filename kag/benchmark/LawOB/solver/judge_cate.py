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

import_modules_from_path("/")

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
extra_key_word = ExtraKeyWord()
with open("/Users/peilong/Downloads/zero_shot/3-7_case_test.json", "r") as f:
    test_cases = json.load(f)
    for value in test_cases:
        answer = value['answer']
        question = value['question']
        key_words = extra_key_word.run(f"Q:{question}\nA:{answer}")
        print(key_words)
        value['key_words'] = key_words
        value['context'] = []
        if "盗窃" in key_words:
            value['type'] = "盗窃"
        elif "诈骗" in key_words:
            value['type'] = "诈骗"

with open("/Users/peilong/Downloads/zero_shot/3-7_case_test_mark.json", "w") as f:
    json.dump(test_cases, f, indent=2, ensure_ascii=False)