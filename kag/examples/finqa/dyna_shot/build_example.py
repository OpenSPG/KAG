import logging
import os
import json

import chromadb


from kag.interface import LLMClient

from kag.common.conf import KAG_CONFIG


from kag.solver.utils import init_prompt_with_fallback

from kag.examples.finqa.dyna_shot.example_prompt import FinQABuildExamplePrompt
from kag.examples.finqa.builder.indexer import convert_finqa_to_md_file


class BuildExamplePipeline:
    def __init__(self, **kwargs):
        """
        Initializes the think-and-act loop class.

        :param max_iterations: Maximum number of iteration to limit the thinking and acting loop, defaults to 3.
        :param reflector: Reflector instance for reflect tasks.
        :param reasoner: Reasoner instance for reasoning about tasks.
        :param generator: Generator instance for generating actions.
        :param memory: Assign memory store type
        """
        super().__init__(**kwargs)
        self.llm_client: LLMClient = LLMClient.from_config(
            KAG_CONFIG.all_config["chat_llm"]
        )
        current_dir = os.path.dirname(os.path.abspath(__file__))
        chromadb_path = os.path.join(current_dir, "chromadb_v2")
        os.makedirs(chromadb_path, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=chromadb_path)
        self.collection = self.chroma_client.create_collection(
            name="finqa_example", get_or_create=True
        )

        self.build_example_prompt = init_prompt_with_fallback(
            "build_example_prompt", "default"
        )

    def build(self, start_index=0):
        error_set = {385, 130, 265, 268, 401, 658, 403, 534, 408, 281, 285, 414, 548, 427, 686, 47, 178, 56, 187, 317, 446, 64, 66, 708, 324, 70, 455, 329, 472, 602, 98, 100, 108, 238, 494, 496, 369, 372, 631, 504, 761, 380, 767}
        train_data_list = self.load_finqa_train_data(_type="test")
        for i, item in enumerate(train_data_list):
            if i < start_index:
                continue
            if i not in error_set:
                continue
            # file_path = convert_finqa_to_md_file(item)
            # with open(file_path, "r", encoding="utf-8") as file:
            #     file_content = file.read()
            try:
                _id = item["id"]
                question = item["qa"]["question"]
                info = ""
                for k, v in item["qa"]["gold_inds"].items():
                    if len(info) > 0:
                        info += "\n"
                    info += f"{k}: {v}"
                # info = str(file_content)
                process = str(item["qa"]["program_re"])
                # answer = str(item["qa"]["answer"])
                params = {
                    "question": question,
                    "info": info,
                    "process": process,
                }
                logging.info("#" * 100)
                logging.info("start,index=%d", i)
                while True:
                    tags, correct, formula = self.llm_client.invoke(
                        variables=params,
                        prompt_op=self.build_example_prompt,
                        with_json_parse=False,
                        with_except=True,
                        with_cache=False,
                    )
                    if tags is None or correct is None or formula is None:
                        logging.error(
                            f"index={i},tags={tags},correct={correct},formula={formula}"
                        )
                        continue
                    break
                doc = question + " tags=" + str(tags)
                logging.info(
                    "index=%d,id=%s\ncorrect=%s\ndoc=%s\nformula=%s",
                    i,
                    _id,
                    correct,
                    doc,
                    formula,
                )
                if "yes" != correct.lower():
                    continue
                self.collection.upsert(
                    documents=[
                        doc,
                    ],
                    metadatas=[
                        {
                            "formula": formula,
                            "gold_inds": json.dumps(
                                item["qa"]["gold_inds"],
                                ensure_ascii=False,
                                sort_keys=True,
                            ),
                            "question": question,
                        }
                    ],
                    ids=[_id],
                )
            except:
                logging.exception("error")
                continue

    def load_finqa_train_data(self, _type="train") -> list:
        """
        load data
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_name = os.path.join(current_dir, "..", "builder", "data", f"{_type}.json")
        with open(file_name, "r", encoding="utf-8") as f:
            data_list = json.load(f)
        print("finqa data list len " + str(len(data_list)))
        for _idx, data in enumerate(data_list):
            data["index"] = _idx
        print(f"type={_type},len={len(data_list)}")
        return data_list

    def search_example(self, query, topn=3):
        rsts = self.collection.query(query_texts=[query], n_results=topn)
        examples = []
        docs = []
        for doc in rsts["documents"][0]:
            docs.append(doc)
        for meta in rsts["metadatas"][0]:
            examples.append(meta["example"])
        return examples, docs


if __name__ == "__main__":
    resp = BuildExamplePipeline()
    resp.build(0)
    # examples, docs = resp.search_example(
    #     "what is the total of home equity lines of credit, tags=['Total Sum']"
    # )
    # for doc in docs:
    #     print(doc)
    # for e in examples:
    #     print(e)
