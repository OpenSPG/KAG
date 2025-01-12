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
                "context": x.get("context", ""),
                "meta": x.get("meta"),
                "kag_trace_log": x.get("kag_trace_log", ""),
                "lightrag_context": y.get("lightrag_context", ""),
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

    def _save_evaluation_responses(self, metrics, reverse_metrics):
        responses = metrics["responses"]
        reverse_responses = reverse_metrics["responses"]
        for item, response, reverse_response in zip(
            self._questions_and_answers, responses, reverse_responses
        ):
            item["response"] = response
            item["reverse_response"] = reverse_response

    def _format_winner(self, score1, score2, *, is_reversed):
        if score1 > score2:
            return "KAG" if not is_reversed else "LightRAG"
        if score1 < score2:
            return "LightRAG" if not is_reversed else "KAG"
        return "None"

    def _format_description(self, description, *, is_reversed):
        if not is_reversed:
            description = description.replace("Answer 1", "KAG")
            description = description.replace("Answer 2", "LightRAG")
        else:
            description = description.replace("Answer 1", "LightRAG")
            description = description.replace("Answer 2", "KAG")
        return description

    def _format_evaluation_response(self, r, *, is_reversed):
        if r is None:
            return "None"
        all_keys = "Comprehensiveness", "Diversity", "Empowerment", "Overall"
        string = ""
        for index, key in enumerate(all_keys):
            if index > 0:
                string += "\n\n"
            string += "**%s**" % key
            string += "\n\n%s Score: %d" % (
                "KAG" if not is_reversed else "LightRAG",
                r[key]["Score 1"],
            )
            string += "\n\n%s Score: %d" % (
                "LightRAG" if not is_reversed else "KAG",
                r[key]["Score 2"],
            )
            string += "\n\nWinner: %s" % self._format_winner(
                r[key]["Score 1"], r[key]["Score 2"], is_reversed=is_reversed
            )
            string += "\n\nExplanation: %s" % self._format_description(
                r[key]["Explanation"], is_reversed=is_reversed
            )
        return string

    def _format_question(self, item):
        string = item["question"]
        string += "\n" + "=" * 80
        string += "\n\nground truth"
        string += "\n" + "-" * 80
        string += "\n" + item["groundtruth_answer"]
        string += "\n\nKAG"
        string += "\n" + "-" * 80
        string += "\n" + item["kag_answer"]
        string += "\n\nLightRAG"
        string += "\n" + "-" * 80
        string += "\n" + item["lightrag_answer"]
        string += "\n\n%s evaluation" % self._evaluator_kwargs["model"]
        string += ": KAG vs LightRAG"
        string += "\n" + "-" * 80
        string += "\n" + self._format_evaluation_response(
            item["response"], is_reversed=False
        )
        string += "\n\n%s evaluation" % self._evaluator_kwargs["model"]
        string += ": LightRAG vs KAG"
        string += "\n" + "-" * 80
        string += "\n" + self._format_evaluation_response(
            item["reverse_response"], is_reversed=True
        )
        return string

    def _format_questions(self):
        string = ""
        for index, item in enumerate(self._questions_and_answers):
            if index > 0:
                string += "\n\n"
            string += self._format_question(item)
        return string

    def _save_evaluation_results(self, metrics, reverse_metrics, average_metrics):
        import io
        import os
        import json
        import time

        data = {
            "metricses": {
                "Metrics: KAG vs LightRAG": metrics["average_metrics"],
                "Metrics: LightRAG vs KAG": reverse_metrics["average_metrics"],
                "Average: KAG vs LightRAG": average_metrics["average_metrics"],
            },
            "questions": self._questions_and_answers,
        }
        start_time = time.time()
        dir_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(dir_path, f"csqa_qfs_res_{start_time}.json")
        with io.open(file_path, "w", encoding="utf-8", newline="\n") as fout:
            json.dump(data, fout, separators=(",", ": "), indent=4, ensure_ascii=False)
            print(file=fout)
        file_path = os.path.join(dir_path, f"csqa_qfs_res_{start_time}.md")
        with io.open(file_path, "w", encoding="utf-8", newline="\n") as fout:
            string = self._format_questions()
            print(string, file=fout)

    def _print_evaluation_results(self, metrics, reverse_metrics, average_metrics):
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

    def run(self):
        metrics = self._compute_summarization_metrics()
        reverse_metrics = self._compute_reverse_summarization_metrics()
        self._save_evaluation_responses(metrics, reverse_metrics)
        average_metrics = self._compute_average_summarization_metrics(
            metrics, reverse_metrics
        )
        self._save_evaluation_results(metrics, reverse_metrics, average_metrics)
        self._print_evaluation_results(metrics, reverse_metrics, average_metrics)


def main():
    evaluator = SummarizationMetricsEvaluator()
    evaluator.run()


if __name__ == "__main__":
    main()
