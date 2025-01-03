class SummarizationMetricsEvaluator(object):
    def __init__(self):
        import os

        self._kag_answers = self._load_kag_answers()
        self._lightrag_answers = self._load_lightrag_answers()
        self._questions_and_answers = self._get_questions_and_answers()
        self._rounds = 3
        self._evaluator_kwargs = {
            "model": "gpt-4o",
            "api_key": os.environ.get("OPENAI_API_KEY"),
            "base_url": "https://api.openai.com/v1",
            "language": "English",
            "retries": 3,
            "max_workers": 50,
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

    def _compute_average_metrics(self, questions, answers1, answers2):
        from kag.common.benchmarks.evaluate import Evaluate

        evaluator = Evaluate()
        metrics = evaluator.getSummarizationMetrics(
            questions, answers1, answers2, **self._evaluator_kwargs
        )
        if self._rounds >= 2:
            all_keys = "Comprehensiveness", "Diversity", "Empowerment", "Overall"
            all_items = "Score 1", "Score 2"
            for _ in range(self._rounds - 1):
                another_metrics = evaluator.getSummarizationMetrics(
                    questions, answers1, answers2, **self._evaluator_kwargs
                )
                for key in all_keys:
                    for item in all_items:
                        metrics["average_metrics"][key][item] += another_metrics[
                            "average_metrics"
                        ][key][item]
            for key in all_keys:
                for item in all_items:
                    metrics["average_metrics"][key][item] /= self._rounds
        return metrics

    def _compute_summarization_metrics(self):
        questions = [item["question"] for item in self._questions_and_answers]
        kag_answers = [item["kag_answer"] for item in self._questions_and_answers]
        lightrag_answers = [
            item["lightrag_answer"] for item in self._questions_and_answers
        ]
        metrics = self._compute_average_metrics(
            questions, kag_answers, lightrag_answers
        )
        return metrics

    def _compute_reverse_summarization_metrics(self):
        questions = [item["question"] for item in self._questions_and_answers]
        kag_answers = [item["kag_answer"] for item in self._questions_and_answers]
        lightrag_answers = [
            item["lightrag_answer"] for item in self._questions_and_answers
        ]
        metrics = self._compute_average_metrics(
            questions, lightrag_answers, kag_answers
        )
        return metrics

    def _compute_average_summarization_metrics(self, metrics, reverse_metrics):
        #
        # Order matters. Here we average the results from different orders.
        #
        # Please refere to:
        #
        #   https://github.com/HKUDS/LightRAG/issues/438
        #
        all_keys = "Comprehensiveness", "Diversity", "Empowerment", "Overall"
        all_items = "Score 1", "Score 2"
        average_metrics = {key: {item: 0.0 for item in all_items} for key in all_keys}
        average_metrics = {"average_metrics": average_metrics}
        for key in all_keys:
            for item, reverse_item in zip(all_items, reversed(all_items)):
                average_metrics["average_metrics"][key][item] = (
                    metrics["average_metrics"][key][item]
                    + reverse_metrics["average_metrics"][key][reverse_item]
                ) / 2
        return average_metrics

    def run(self):
        metrics = self._compute_summarization_metrics()
        reverse_metrics = self._compute_reverse_summarization_metrics()
        average_metrics = self._compute_average_summarization_metrics(
            metrics, reverse_metrics
        )
        all_keys = "Comprehensiveness", "Diversity", "Empowerment", "Overall"
        all_items = "Score 1", "Score 2"
        titles = (
            "Metrics: KAG vs LightRAG",
            "Metrics: LightRAG vs KAG",
            "Average: KAG vs LightRAG",
        )
        metricses = (
            metrics,
            reverse_metrics,
            average_metrics,
        )
        string = ""
        for index, (title, metrics) in enumerate(zip(titles, metricses)):
            if index > 0:
                string += "\n\n"
            string += title
            string += "\n" + "-" * 40
            for key in all_keys:
                string += "\n%s:" % key
                for i, item in enumerate(all_items):
                    if i > 0:
                        string += " vs"
                    string += " %.2f" % metrics["average_metrics"][key][item]
        print(string)


def main():
    evaluator = SummarizationMetricsEvaluator()
    evaluator.run()


if __name__ == "__main__":
    main()
