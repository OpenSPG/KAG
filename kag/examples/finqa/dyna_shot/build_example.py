import logging
import os
import json

import chromadb


from kag.interface import LLMClient

from kag.common.conf import KAG_CONFIG


from kag.solver.utils import init_prompt_with_fallback

from kag.examples.finqa.dyna_shot.example_prompt import FinQABuildExamplePrompt


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
        chromadb_path = os.path.join(current_dir, "chromadb")
        os.makedirs(chromadb_path, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=chromadb_path)
        self.collection = self.chroma_client.create_collection(
            name="finqa_example", get_or_create=True
        )

        self.build_example_prompt = init_prompt_with_fallback(
            "build_example_prompt", "default"
        )

    def build(self):
        train_data_list = self.load_finqa_train_data() + self.load_finqa_train_data(
            _type="test"
        )
        for i, item in enumerate(train_data_list):
            _id = item["id"]
            question = item["qa"]["question"]
            info = str(item["qa"]["gold_inds"])
            process = str(item["qa"]["program_re"])
            params = {"question": question, "info": info, "process": process}
            solution, tags, example = self.llm_client.invoke(
                variables=params,
                prompt_op=self.build_example_prompt,
                with_json_parse=False,
                with_except=True,
            )
            doc = question + " tags=" + str(tags)
            logging.info("index=%d,id=%s,%s,doc=%s\n%s", i, _id, solution, doc, example)
            if "correct" != solution.lower():
                continue
            self.collection.upsert(
                documents=[
                    doc,
                ],
                metadatas=[{"example": example}],
                ids=[_id],
            )

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
        return data_list

    def search_example(self, query, topn=3):
        rsts = self.collection.query(query_texts=[query], n_results=topn)
        examples = []
        for meta in rsts["metadatas"][0]:
            examples.append(meta["example"])
        return examples


if __name__ == "__main__":
    resp = BuildExamplePipeline()
    resp.build()
    # examples = resp.search_example("what is the total of home equity lines of credit")
    # for e in examples:
    #     print(e)
