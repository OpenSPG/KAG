from tenacity import retry, stop_after_attempt


class FactualCorrectnessEvaluator(object):
    def __init__(self):
        import os

        self._kag_answers = self._load_kag_answers()
        self._lightrag_answers = self._load_lightrag_answers()
        self._questions_and_answers = self._get_questions_and_answers()
        self._evaluator_llm_kwargs = {
            "model": "gpt-4o",
            "api_key": os.environ.get("OPENAI_API_KEY"),
            "base_url": "https://api.openai.com/v1",
        }

    def _load_kag_answers(self):
        import io
        import os
        import json

        dir_path = os.path.dirname(os.path.abspath(__file__))
        dir_path = os.path.join(dir_path, "data")
        file_path = os.path.join(dir_path, "csqa_kag_answers.json")
        with io.open(file_path, "r", encoding="utf-8", newline="\n") as fin:
            kag_answers = json.load(fin)
        return kag_answers

    def _load_lightrag_answers(self):
        import io
        import os
        import json

        dir_path = os.path.dirname(os.path.abspath(__file__))
        dir_path = os.path.join(dir_path, "data")
        file_path = os.path.join(dir_path, "csqa_lightrag_answers.json")
        with io.open(file_path, "r", encoding="utf-8", newline="\n") as fin:
            lightrag_answers = json.load(fin)
        return lightrag_answers

    def _get_questions_and_answers(self):
        result = []
        for x, y in zip(self._kag_answers, self._lightrag_answers):
            assert x["input"] == y["input"]
            item = {
                "question": x["input"],
                "groundtruth_answer": " ".join(x["answers"]),
                "kag_answer": x["kag_answer"],
                "lightrag_answer": y["lightrag_answer"],
            }
            result.append(item)
        return result

    @retry(stop=stop_after_attempt(3))
    def _check_factual_correctness(self, item):
        #
        # We tried the factual correctness metric in RAGAS initially,
        # but the output was quite unstable.
        #
        # This function sets the `n`, `temperature` and `top_p` parameters
        # to increase the model's determinism as described in the G-EVAL
        # paper, but the output remains somewhat unstable.
        #
        import json
        from openai import OpenAI

        prompt = 'Given the following QUESTION, GROUND-TRUTH ANSWER and ANSWER you must analyze the provided answer and determine whether it is faithful to the contents of the GROUND-TRUTH ANSWER.\n The ANSWER must not offer new information beyond the context provided in the GROUND-TRUTH ANSWER. The ANSWER also must not contradict information provided in the GROUND-TRUTH ANSWER. Output your final verdict by strictly following this format: "PASS" if the answer is faithful to the GROUND-TRUTH ANSWER and "FAIL" if the answer is not faithful to the GROUND-TRUTH ANSWER. Show your reasoning.\n --\n QUESTION:\n{}\n --\n GROUND-TRUTH ANSWER:{}\n--\nANSWER:{}\n--\n Your output should be in JSON FORMAT with the keys "REASONING" and "SCORE": {{"REASONING": <your reasoning as bullet points>, "SCORE": <your final score>}}'.format(
            item["question"], item["groundtruth_answer"], item["answer"]
        )
        client = OpenAI(
            api_key=self._evaluator_llm_kwargs["api_key"],
            base_url=self._evaluator_llm_kwargs["base_url"],
        )
        n = 10
        response = client.chat.completions.create(
            model=self._evaluator_llm_kwargs["model"],
            messages=[
                {"role": "user", "content": prompt},
            ],
            timeout=600,
            n=n,
            temperature=1.0,
            top_p=1.0,
        )
        assert len(response.choices) == n
        ans = 0.0
        for i in range(n):
            content = response.choices[i].message.content
            if content.startswith("```json") and content.endswith("```"):
                content = content[7:-3].strip()
            result = json.loads(content)
            print(prompt, result["SCORE"])
            assert result["SCORE"] in ("PASS", "FAIL")
            ans += result["SCORE"] == "PASS"
        ans /= n
        return ans

    def _process_item(self, item):
        results = {}
        results["kag"] = self._check_factual_correctness(
            {
                "question": item["question"],
                "groundtruth_answer": item["groundtruth_answer"],
                "answer": item["kag_answer"],
            }
        )
        results["lightrag"] = self._check_factual_correctness(
            {
                "question": item["question"],
                "groundtruth_answer": item["groundtruth_answer"],
                "answer": item["lightrag_answer"],
            }
        )
        return results

    def _get_metrics(self):
        from tqdm import tqdm
        from concurrent.futures import ThreadPoolExecutor, as_completed

        max_workers = 50
        all_keys = "kag", "lightrag"
        metrics = {key: 0.0 for key in all_keys}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self._process_item, item)
                for item in self._questions_and_answers
            ]
            for future in tqdm(
                as_completed(futures), total=len(futures), desc="Evaluating: "
            ):
                results = future.result()
                for key in all_keys:
                    metrics[key] += results[key]
        for key in all_keys:
            metrics[key] /= len(self._questions_and_answers)
        return metrics

    def run(self):
        metrics = self._get_metrics()
        print(metrics)


def main():
    evaluator = FactualCorrectnessEvaluator()
    evaluator.run()


if __name__ == "__main__":
    main()
