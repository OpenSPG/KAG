import logging
import re
import os
import json

import chromadb

import re
import logging
from typing import List

from kag.interface import PromptABC


from kag.interface import LLMClient

from kag.common.conf import KAG_CONFIG


from kag.solver.utils import init_prompt_with_fallback

from kag.examples.finqa.dyna_shot.example_prompt import FinQABuildExamplePrompt
from kag.examples.finqa.solver.prompt.question_classify import FinQAQuestionClassify
from kag.examples.finqa.builder.indexer import convert_finqa_to_md_file

REFINE_ID = {
    512,
    1025,
    771,
    772,
    265,
    1035,
    12,
    268,
    1040,
    20,
    534,
    281,
    285,
    542,
    548,
    39,
    47,
    820,
    53,
    56,
    1082,
    317,
    64,
    833,
    66,
    324,
    325,
    70,
    583,
    329,
    854,
    599,
    1112,
    87,
    602,
    1114,
    94,
    1121,
    98,
    100,
    359,
    108,
    369,
    372,
    119,
    631,
    380,
    385,
    130,
    401,
    658,
    403,
    408,
    410,
    414,
    677,
    427,
    173,
    686,
    434,
    178,
    183,
    187,
    446,
    703,
    449,
    708,
    455,
    201,
    973,
    983,
    472,
    745,
    233,
    238,
    495,
    1007,
    494,
    496,
    246,
    504,
    761,
    1021,
    1022,
    767,
}


@PromptABC.register("default_refine_example_prompt")
class FinQARefineExamplePrompt(PromptABC):
    template_zh = """
# 任务
你的任务是根据已有的题目及其解题方法，构造类似的题目。类似题目的解题方法和公式，与已有题目必须完全一样。
我会给你几个构造类似题目的建议和例子，请仔细阅读。

# 构造类似题目的建议
1. 题目中出现时间信息的，可以修改时间来构造新题目，例如：from 2010 to 2012，其他部分不变，可以改成from 2011 to 2013等。
2. 如果时间不适合修改，则修改概念。例如：净利润增长百分比，可以修改为营业收入增长百分比。
3. 如果1和2两个方法都不适合修改，那么就简单修改一下描述方式，重新组织一下语言。

# 例子
## 修改时间的例子
### Input
Question: what percentage of the minimum annual future rental commitment under operating leases that have initial or remaining non-cancelable lease terms is due in 2019?
Formula: Percentage Due in 2019 = (Rental Commitment in 2019 / Total Rental Commitment) * 100
### Output
你的思考过程...略
<Question>what percentage of the minimum annual future rental commitment under operating leases that have initial or remaining non-cancelable lease terms is due in 2013?</Question>
<Formula>Percentage Due in 2013 = (Rental Commitment in 2013 / Total Rental Commitment) * 100<Formula>

## 修改概念
### Input
Question: what portion of the total net reorganization items are related to professional fees?
Formula: Portion of Professional Fees = Professional Fees / Total Net Reorganization Items
### Output
你的思考过程...略
<Question>What portion of the total net reorganization items are related to employee severance costs?</Question>
<Formula>Portion of Employee Severance Costs = Employee Severance Costs / Total Net Reorganization Items</Formula>

## 修改描述方式
### Input
Question: what percentage of total shares repurchased were purchased in november?
Formula: Percentage of Shares Repurchased in November = (Number of Shares Repurchased in November / Total Number of Shares Repurchased) * 100
### Output
你的思考过程...略
<Question>What percentage of the total shares repurchased were bought in November?</Question>
<Formula>Percentage of Shares Repurchased in November = (Number of Shares Repurchased in November / Total Number of Shares Repurchased) * 100</Formula>

# 真正的输入
$input

""".strip()

    template_en = """
# Task
Your task is to create similar questions based on an existing question and its solution method. The solution method and formula for the new question must be exactly the same as those for the original question.
I will provide a few suggestions and examples on how to construct similar questions. Please read them carefully.

# Suggestions for Constructing Similar Questions
1. If the question includes time information, you can modify the timeline to create a new question. For example: "from 2010 to 2012," keeping the other parts unchanged, can be modified into "from 2011 to 2013," etc.
2. If the time information cannot be reasonably altered, change the concept instead. For example: "percentage increase in net profit" can be modified into "percentage increase in revenue."
3. If neither of the first two methods is applicable, simply reword or rephrase the description while keeping the original meaning the same.

# Examples
## Example of Modifying Time
### Input
Question: what percentage of the minimum annual future rental commitment under operating leases that have initial or remaining non-cancelable lease terms is due in 2019?
Formula: Percentage Due in 2019 = (Rental Commitment in 2019 / Total Rental Commitment) * 100

### Output
Your thought process... omitted
<Question>what percentage of the minimum annual future rental commitment under operating leases that have initial or remaining non-cancelable lease terms is due in 2013?</Question>
<Formula>Percentage Due in 2013 = (Rental Commitment in 2013 / Total Rental Commitment) * 100</Formula>

## Example of Modifying Concept
### Input
Question: what portion of the total net reorganization items are related to professional fees?
Formula: Portion of Professional Fees = Professional Fees / Total Net Reorganization Items

### Output
Your thought process... omitted
<Question>What portion of the total net reorganization items are related to employee severance costs?</Question>
<Formula>Portion of Employee Severance Costs = Employee Severance Costs / Total Net Reorganization Items</Formula>

## Example of Rephrasing
### Input
Question: what percentage of total shares repurchased were purchased in november?
Formula: Percentage of Shares Repurchased in November = (Number of Shares Repurchased in November / Total Number of Shares Repurchased) * 100

### Output
Your thought process... omitted
<Question>What percentage of the total shares repurchased were bought in November?</Question>
<Formula>Percentage of Shares Repurchased in November = (Number of Shares Repurchased in November / Total Number of Shares Repurchased) * 100</Formula>

# Actual Input
$input
"""

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        question_pattern = r"<Question>(.*?)</Question>"
        formula_pattern = r"<Formula>(.*?)</Formula>"
        question_match = re.search(question_pattern, response, re.DOTALL)
        formula_match = re.search(formula_pattern, response, re.DOTALL)
        question_str = question_match.group(1).strip() if question_match else None
        formula_str = formula_match.group(1).strip() if formula_match else None
        return question_str, formula_str


class RefineExamplePipeline:
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

        self.refine_example_prompt = init_prompt_with_fallback(
            "refine_example_prompt", "default"
        )

        self.question_classify_prompt = init_prompt_with_fallback(
            "question_classify", "table"
        )

    def question_classify(self, question):
        llm: LLMClient = self.llm_client
        params = {"question": question}
        tags = llm.invoke(
            variables=params,
            prompt_op=self.question_classify_prompt,
            with_json_parse=False,
            with_except=True,
        )
        return tags

    def retrieval_examples(self, question, tags, topn=3):
        doc = question + " tags=" + str(tags)
        rsts = self.collection.query(query_texts=[doc], n_results=topn)
        examples = []
        for meta in rsts["metadatas"][0]:
            example = f"Question:{meta['question']}\nFormula:{meta['formula']}"
            examples.append(example)
            # examples.append(meta["example"])
        return examples

    def _to_example_str(self, examples):
        e_str = ""
        for i, e in enumerate(examples):
            e_str += f"\n\n### {i}\n{e}"
        return e_str.strip()

    def refine(self, start_index=0):
        test_data_list = self.load_finqa_train_data("test")
        for i, item in enumerate(test_data_list):
            if i < start_index:
                continue
            if i not in REFINE_ID:
                continue
            try:
                _id = item["id"]
                question = item["qa"]["question"]
                # 先构造example
                info = ""
                for k, v in item["qa"]["gold_inds"].items():
                    if len(info) > 0:
                        info += "\n"
                    info += f"{k}: {v}"
                process = str(item["qa"]["program_re"])
                params = {
                    "question": question,
                    "info": info,
                    "process": process,
                }
                with_cache = True
                while True:
                    tags, correct, formula = self.llm_client.invoke(
                        variables=params,
                        prompt_op=self.build_example_prompt,
                        with_json_parse=False,
                        with_except=True,
                        with_cache=with_cache,
                    )
                    if tags is None or correct is None or formula is None:
                        with_cache = False
                        logging.error(
                            f"index={i},tags={tags},correct={correct},formula={formula}"
                        )
                        continue
                    break

                # 再修改example
                params = {"input": f"Question: {question}\nFormula: {formula}"}
                with_cache = True
                while True:
                    question2, formula2 = self.llm_client.invoke(
                        variables=params,
                        prompt_op=self.refine_example_prompt,
                        with_json_parse=False,
                        with_except=True,
                        with_cache=with_cache,
                    )
                    if question2 is None or formula2 is None:
                        with_cache = False
                        logging.error(
                            f"index={i},question={question},question2={question2},formula2={formula2}"
                        )
                        continue
                    break

                doc = question2 + " tags=" + str(tags)
                logging.info(
                    "index=%d\nquestion=%s\ndoc=%s\nformula=%s",
                    i,
                    question,
                    doc,
                    formula2,
                )

                _id = f"domain_knowledge_{i}"
                self.collection.upsert(
                    documents=[
                        doc,
                    ],
                    metadatas=[
                        {
                            "formula": formula2,
                            "question": question2,
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


if __name__ == "__main__":
    resp = RefineExamplePipeline()
    resp.refine(820)
