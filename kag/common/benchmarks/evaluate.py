from typing import List
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

from .LLMJudger import LLMJudger
from .evaUtils import get_em_f1
from .evaUtils import compare_summarization_answers
from .evaUtils import compute_rouge
from ..conf import KAG_CONFIG
from ..config import get_default_chat_llm_config
from ..utils import processing_phrases
from enum import Enum

from ...interface import LLMClient


class MetricType(Enum):
    EM_F1 = "em_f1"
    LLM = "llm"
    ROUGE_L = "rouge-l"
    SIMILARITY = "similarity"


class Evaluate:
    """
    provide evaluation for benchmarks, such as em、f1、answer_similarity, answer_correctness
    """

    def __init__(
        self, embedding_factory="text-embedding-ada-002", metrics: list = None
    ):
        self.embedding_factory = embedding_factory
        self.metrics = metrics or [MetricType.EM_F1, MetricType.LLM]
        self.llm_name = "llm_judge"

    def generate_id(self, title, content):
        return processing_phrases(f"{title}\n{content}").replace("\n", "")

    def evaForSimilarity(self, predictionlist: List[str], goldlist: List[str]):
        """
        evaluate the similarity between prediction and gold #TODO
        """
        # data_samples = {
        #     'question': [],
        #     'answer': predictionlist,
        #     'ground_truth': goldlist
        # }
        # dataset = Dataset.from_dict(data_samples)
        # run_config = RunConfig(timeout=240, thread_timeout=240, max_workers=16)
        # embeddings = embedding_factory(self.embedding_factory, run_config)
        #
        # score = evaluate(dataset, metrics=[answer_similarity], embeddings = embeddings, run_config=run_config)
        # return np.average(score.to_pandas()[['answer_similarity']])
        return {"similarity": 0.0}

    def compute_rouge(self, predictionlist: List[str], goldlist: List[str]):
        rouge_scores = compute_rouge(predictionlist, goldlist)
        rouge_ls = [score["rouge-l"]["f"] for score in rouge_scores]
        average_rouge_l = sum(rouge_ls) / len(rouge_ls)
        return {"rouge-L": average_rouge_l}

    def convert_chunk_data_2_str(self, predictionlist: list):
        ret = []
        for chunk_data in predictionlist:
            title = chunk_data["title"]
            content = chunk_data["content"]
            content = f"{title}\n{content}"
            for i in range(0, 10):
                content = content.replace(f"_split_{i}", "")
            content = processing_phrases(content).replace("\n", "")
            ret.append(content)
        return ret

    def _extract_text_only(self, text, mode="all"):
        """
        Extract text content only, removing all symbols including newlines

        Parameters:
        text: input text
        mode: extraction mode ('all', 'chinese_only')
            - 'all': extract Chinese characters, English letters and numbers
            - 'chinese_only': extract only Chinese characters

        Returns:
        str: extracted text content (lowercase for English)
        """
        if mode == "chinese_only":
            # Use regex to keep only Chinese characters, remove all other content
            text_only = re.sub(r"[^\u4e00-\u9fa5]", "", str(text))
            return text_only
        else:
            # Use regex to keep only Chinese characters, English letters and numbers, remove all symbols (including newlines, spaces, etc.)
            text_only = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", str(text))
            # Convert to lowercase
            return text_only.lower()

    def _tokenize_chinese(self, text):
        """
        Tokenize Chinese text into word set

        Parameters:
        text: Chinese text

        Returns:
        set: set of Chinese words/characters
        """
        try:
            # Try to use jieba for word segmentation
            import jieba

            words = jieba.lcut(text)
            # Filter out single characters and short words, keep meaningful words
            meaningful_words = [word.strip() for word in words if len(word.strip()) > 1]
            # If no meaningful words found, fall back to character-level
            if not meaningful_words:
                meaningful_words = [char for char in text if char.strip()]
            return set(meaningful_words)
        except ImportError:
            # Fallback to character-level tokenization if jieba not available
            return set([char for char in text if char.strip()])

    def _calculate_set_similarity(self, set1, set2):
        """
        Calculate similarity between two sets using Jaccard similarity

        Parameters:
        set1: first set
        set2: second set

        Returns:
        float: Jaccard similarity (0.0 to 1.0)
        """
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    def fuzzy_intersection(
        self, gold_set, prediction_set, fuzzy_mode="all", similarity_threshold=0.2
    ):
        """
        Calculate intersection using fuzzy matching, only matching text content and ignoring symbols

        Parameters:
        gold_set: ground truth set
        prediction_set: prediction result set
        fuzzy_mode: text extraction mode ('all', 'chinese_only')
        similarity_threshold: minimum similarity threshold for chinese_only mode (0.0 to 1.0)

        Returns:
        int: number of matches
        """
        matches = 0
        for gold_item in gold_set:
            gold_text = self._extract_text_only(gold_item, fuzzy_mode)

            for pred_item in prediction_set:
                pred_text = self._extract_text_only(pred_item, fuzzy_mode)

                if fuzzy_mode == "chinese_only":
                    # Use tokenization and set similarity for Chinese text
                    gold_tokens = self._tokenize_chinese(gold_text)
                    pred_tokens = self._tokenize_chinese(pred_text)
                    similarity = self._calculate_set_similarity(
                        gold_tokens, pred_tokens
                    )

                    if similarity >= similarity_threshold:
                        matches += 1
                        break  # Break inner loop after finding match to avoid duplicate counting
                    if gold_text in pred_text or pred_text in gold_text:
                        matches += 1
                        break
                else:
                    # Use original substring matching for 'all' mode
                    if gold_text in pred_text or pred_text in gold_text:
                        matches += 1
                        break  # Break inner loop after finding match to avoid duplicate counting
        return matches

    def fuzzy_difference(
        self, gold_set, prediction_set, fuzzy_mode="all", similarity_threshold=0.2
    ):
        """
        Calculate difference using fuzzy matching, only matching text content and ignoring symbols
        Returns the number of items in gold_set but not in prediction_set

        Parameters:
        gold_set: ground truth set
        prediction_set: prediction result set
        fuzzy_mode: text extraction mode ('all', 'chinese_only')
        similarity_threshold: minimum similarity threshold for chinese_only mode (0.0 to 1.0)

        Returns:
        int: number of items in difference set
        """
        unmatched = 0
        for gold_item in gold_set:
            gold_text = self._extract_text_only(gold_item, fuzzy_mode)
            found_match = False

            for pred_item in prediction_set:
                pred_text = self._extract_text_only(pred_item, fuzzy_mode)

                if fuzzy_mode == "chinese_only":
                    # Use tokenization and set similarity for Chinese text
                    gold_tokens = self._tokenize_chinese(gold_text)
                    pred_tokens = self._tokenize_chinese(pred_text)
                    similarity = self._calculate_set_similarity(
                        gold_tokens, pred_tokens
                    )

                    if similarity >= similarity_threshold:
                        found_match = True
                        break
                    if gold_text in pred_text or pred_text in gold_text:
                        found_match = True
                        break
                else:
                    # Use original substring matching for 'all' mode
                    if gold_text in pred_text or pred_text in gold_text:
                        found_match = True
                        break

            if not found_match:
                unmatched += 1
        return unmatched

    def recall_top(
        self,
        predictionlist: list,
        goldlist: List[str],
        is_chunk_data: bool = True,
        fuzzy_mode: str = "all",
        similarity_threshold: float = 0.2,
    ):
        """
        Calculate recall for top-3, top-5, and all predictions.

        Parameters:
        predictionlist (List[str]): List of predicted values from the model.
        goldlist (List[str]): List of actual ground truth values.
        is_chunk_data (bool): Whether predictionlist contains chunk data.
        fuzzy_mode (str): Text extraction mode ('all', 'chinese_only').
        similarity_threshold (float): Minimum similarity threshold for chinese_only mode (0.0 to 1.0).

        Returns:
        dict: Dictionary containing recall for top-3, top-5, and all predictions.
        """
        if is_chunk_data:
            predictionlist = self.convert_chunk_data_2_str(predictionlist)
        # Split predictions into lists of top-3 and top-5
        top3_predictions = predictionlist[:3]
        top5_predictions = predictionlist[:5]

        gold_set = set(goldlist)
        all_set = set(predictionlist)
        top3_set = set(top3_predictions)
        top5_set = set(top5_predictions)

        # Use fuzzy matching instead of exact intersection
        true_positives_top3 = self.fuzzy_intersection(
            gold_set, top3_set, fuzzy_mode, similarity_threshold
        )
        false_negatives_top3 = self.fuzzy_difference(
            gold_set, top3_set, fuzzy_mode, similarity_threshold
        )

        recall_top3 = (
            true_positives_top3 / (true_positives_top3 + false_negatives_top3)
            if (true_positives_top3 + false_negatives_top3) > 0
            else 0.0
        )

        # Update counters for top-5
        true_positives_top5 = self.fuzzy_intersection(
            gold_set, top5_set, fuzzy_mode, similarity_threshold
        )
        false_negatives_top5 = self.fuzzy_difference(
            gold_set, top5_set, fuzzy_mode, similarity_threshold
        )

        recall_top5 = (
            true_positives_top5 / (true_positives_top5 + false_negatives_top5)
            if (true_positives_top5 + false_negatives_top5) > 0
            else 0.0
        )
        # Update counters for all
        true_positives_all = self.fuzzy_intersection(
            gold_set, all_set, fuzzy_mode, similarity_threshold
        )
        false_negatives_all = self.fuzzy_difference(
            gold_set, all_set, fuzzy_mode, similarity_threshold
        )

        recall_all = (
            true_positives_all / (true_positives_all + false_negatives_all)
            if (true_positives_all + false_negatives_all) > 0
            else 0.0
        )

        return {
            "recall_top3": recall_top3,
            "recall_top5": recall_top5,
            "recall_all": recall_all,
        }

    def getEmAndF1(self, predictionlist: List[str], goldlist: List[str]):
        """
        Calculates and returns evaluation metrics between predictions and ground truths.

        This function evaluates the match between predictions and ground truths by calculating
        the exact match (EM) and F1 score, as well as answer similarity.

        Parameters:
        predictionlist (List[str]): List of predicted values from the model.
        goldlist (List[str]): List of actual ground truth values.

        Returns:
        dict: Dictionary containing EM, F1 score, and answer similarity.
        """
        # Initialize total metrics
        total_metrics = {"em": 0.0, "f1": 0.0, "answer_similarity": 0.0}

        # Iterate over prediction and gold lists to calculate EM and F1 scores
        for prediction, gold in zip(predictionlist, goldlist):
            em, f1 = get_em_f1(
                prediction, gold
            )  # Call external function to calculate EM and F1
            total_metrics["em"] += em  # Accumulate EM score
            total_metrics["f1"] += f1  # Accumulate F1 score

        # Calculate average EM and F1 scores
        total_metrics["em"] /= len(predictionlist)
        total_metrics["f1"] /= len(predictionlist)
        return total_metrics

    def getBenchMark(
        self, questionlist: List[str], predictionlist: List[str], goldlist: List[str]
    ):
        total_metrics = {}
        for metric in self.metrics:
            if metric == MetricType.EM_F1:
                total_metrics.update(self.getEmAndF1(predictionlist, goldlist))
            if metric == MetricType.LLM:
                if "llm_judge" in KAG_CONFIG.all_config:
                    llm_conf = KAG_CONFIG.all_config["llm_judge"]
                else:
                    llm_conf = get_default_chat_llm_config()
                llm_conf["enable_check"] = False
                llm_client = LLMClient.from_config(llm_conf)
                total_metrics.update(
                    self.getLLMBenchMark(
                        llm_client, questionlist, predictionlist, goldlist
                    )
                )
            if metric == MetricType.ROUGE_L:
                total_metrics.update(self.compute_rouge(predictionlist, goldlist))
            if metric == MetricType.SIMILARITY:
                total_metrics.update(self.evaForSimilarity(predictionlist, goldlist))
        # Return evaluation metrics dictionary
        return total_metrics

    def getLLMBenchMark(
        self,
        llm_client,
        questionList: List[str],
        predictionlist: List[str],
        goldlist: List[str],
    ):
        """
        Calculates and returns evaluation metrics between predictions and ground truths.

        This function evaluates the match between predictions and ground truths by calculating
        the exact match (EM) and F1 score, as well as answer similarity.

        Parameters:
        predictionlist (List[str]): List of predicted values from the model.
        goldlist (List[str]): List of actual ground truth values.

        Returns:
        dict: Dictionary containing EM, F1 score, and answer similarity.
        """
        # Initialize total metrics
        total_metrics = {}
        llm_judger = LLMJudger(llm=llm_client)

        # llm = LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])
        # Iterate over prediction and gold lists to calculate EM and F1 scores
        hits = 0
        for question, prediction, gold in tqdm(
            zip(questionList, predictionlist, goldlist),
            total=len(questionList),
            desc="Evaluating predictions",
        ):
            response = llm_judger.judge_by_llm(
                question=question, prediction=prediction, gold=gold
            )
            if response.lower() == "true":
                hits += 1

        # Calculate consistency
        total_metrics["LLM-Accuracy"] = float(hits) / len(predictionlist)
        return total_metrics

    def getSummarizationMetrics(
        self,
        queries: List[str],
        answers1: List[str],
        answers2: List[str],
        *,
        api_key="EMPTY",
        base_url="http://127.0.0.1:38080/v1",
        model="gpt-4o-mini",
        language="English",
        retries=3,
        max_workers=50,
    ):
        """
        Calculates and returns QFS (query-focused summarization) evaluation metrics
        for the given queries, answers1 and answers2.

        This function evaluates the triple (query, answer1, answer2) by feeding it
        into an evaluating LLM specified as `api_key`, `base_url` and `model`.

        Parameters:
        queries (List[str]): List of queries.
        answers1 (List[str]): List of answers generated by an LLM (LLM-1).
        answers2 (List[str]): List of answers generated by another LLM (LLM-2).
        api_key (str): API key to use when invoke the evaluating LLM.
        base_url (str): base url to use when invoke the evaluating LLM.
        model (str): model name to use when invoke the evaluating LLM.
        language (str): language of the explanation
        retries (int): number of retries
        max_workers (int): number of workers

        Returns:
        dict: Dictionary containing the average metrics and the responses
              generated by the evaluating LLM.
        """
        responses = [None] * len(queries)
        all_keys = "Comprehensiveness", "Diversity", "Empowerment", "Overall"
        all_items = "Score 1", "Score 2"
        average_metrics = {key: {item: 0.0 for item in all_items} for key in all_keys}
        success_count = 0

        def process_sample(index, query, answer1, answer2):
            metrics = compare_summarization_answers(
                query,
                answer1,
                answer2,
                api_key=api_key,
                base_url=base_url,
                model=model,
                language=language,
                retries=retries,
            )
            if metrics is None:
                print(
                    f"fail to compare answers of query {index + 1}.\n"
                    f"      query: {query}\n"
                    f"    answer1: {answer1}\n"
                    f"    answer2: {answer2}\n"
                )
            else:
                responses[index] = metrics
            return metrics

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process_sample, index, query, answer1, answer2)
                for index, (query, answer1, answer2) in enumerate(
                    zip(queries, answers1, answers2)
                )
            ]
            for future in tqdm(
                as_completed(futures), total=len(futures), desc="Evaluating: "
            ):
                metrics = future.result()
                if metrics is not None:
                    for key in all_keys:
                        for item in all_items:
                            average_metrics[key][item] += metrics[key][item]
                    success_count += 1
        if success_count > 0:
            for key in all_keys:
                for item in all_items:
                    average_metrics[key][item] /= success_count
        result = {
            "average_metrics": average_metrics,
            "responses": responses,
        }
        return result
