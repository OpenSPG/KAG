import os
from kag.common.conf import KAG_CONFIG
from kag.common.benchmarks.evaluate import Evaluate
from kag.interface.common.llm_client import LLMClient
import logging
import json
from typing import List, Dict, Any
import argparse

logger = logging.getLogger(__name__)


def extract_answer_from_prediction(prediction: str) -> str:
    """Placeholder: Extracts answer from prediction string."""
    if isinstance(prediction, str) and "答案:" in prediction:
        parts = prediction.split("答案:")
        if len(parts) > 1:
            return parts[-1].strip()
    return str(prediction).strip()


class PrqaEvaluate(Evaluate):
    def run_qa_evaluation(
        self, qa_data: List[Dict[str, Any]], llm_client: LLMClient
    ) -> Dict[str, Any]:
        """
        Runs the complete evaluation for PRQA data using inherited Evaluate methods.
        Expects qa_data to contain 'question', 'prediction', 'answer'.
        """
        questions = []
        predictions_extracted = []
        gold_answers = []

        logger.info(f"Starting comprehensive evaluation for {len(qa_data)} QA pairs.")

        valid_pairs = 0
        for item in qa_data:
            if "prediction" not in item or item["prediction"] is None:
                logger.warning(
                    f"ID {item.get('id', 'N/A')} missing prediction, skipping evaluation."
                )
                continue
            if "answer" not in item or item["answer"] is None:
                logger.warning(
                    f"ID {item.get('id', 'N/A')} missing answer, skipping evaluation."
                )
                continue
            if "question" not in item or item["question"] is None:
                logger.warning(
                    f"ID {item.get('id', 'N/A')} missing question, skipping evaluation."
                )
                continue

            questions.append(item["question"])
            predictions_extracted.append(
                extract_answer_from_prediction(item["prediction"])
            )
            ans = item["answer"]
            gold_answers.append(str(ans[0]) if isinstance(ans, list) else str(ans))
            valid_pairs += 1

        if not predictions_extracted:
            logger.error("No valid predictions found to evaluate.")
            return {"error": "No valid data for evaluation"}

        # --- Calculate Metrics using inherited methods ---
        logger.info("Calculating LLM Consistency metrics...")
        llm_metrics = self.getBenchMark(questions, predictions_extracted, gold_answers)
        logger.info(f"Evaluation completed. Results: {llm_metrics}")
        return llm_metrics


def parse_result_file(file_path):
    result_data = []
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read().strip().split("\n\n")  # 分块处理
        for block in content:

            id_ = question = prediction = None

            for line in block.strip().split("\n"):
                if line.startswith("序号:"):
                    id_ = line.split("序号:")[1].strip()
                elif line.startswith("问题:"):
                    question = line.split("问题:")[1].strip()
                elif line.startswith("答案:"):
                    prediction = line.split("答案:")[1].strip()

            if id_ and question and prediction:
                result_data.append(
                    {"id": id_, "question": question, "prediction": prediction}
                )
            else:
                print(f"Skipping block due to missing data:\n{block}")
    return result_data


def parse_gold_answer_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        gold_answer_data = json.load(file)
    return gold_answer_data.get("PeopleRelationshipsQA", [])


def generate_output_data(result_data, gold_answer_data):
    output_data = []
    for result_entry in result_data:
        id_ = result_entry["id"]
        question = result_entry["question"]
        prediction = result_entry["prediction"]

        # 在 gold_answer.json 中寻找对应 answer
        answer = []
        for qa_item in gold_answer_data:
            if id_ in qa_item:
                answer = qa_item[id_]
                break

        output_data.append(
            {
                "id": id_,
                "question": question,
                "answer": answer,
                "prediction": prediction,
            }
        )
    return output_data


if __name__ == "__main__":
    dir_path = os.path.dirname(__file__)

    prediction_file_path = os.path.join(dir_path, "solver/data/result.txt")
    gold_answer_file_path = os.path.join(dir_path, "solver/data/gold_answer.json")
    data_file_path = os.path.join(dir_path, "solver/data/res.json")
    output_file_path = os.path.join(dir_path, "solver/data/evaluation_results.json")

    result_data = parse_result_file(prediction_file_path)
    gold_answer_data = parse_gold_answer_file(gold_answer_file_path)
    output_data = generate_output_data(result_data, gold_answer_data)

    with open(data_file_path, "w", encoding="utf-8") as output_file:
        json.dump(output_data, output_file, ensure_ascii=False, indent=4)

    # --- Step 1: Load Existing Data with Predictions ---
    with open(data_file_path, "r", encoding="utf-8") as f:
        qa_data_with_predictions = json.load(f)

    # --- Step 2: Perform Comprehensive Evaluation ---
    llm_config = KAG_CONFIG.all_config["chat_llm"]
    llm_client_for_eval = LLMClient.from_config(llm_config)

    evaluator = PrqaEvaluate()
    # Run the comprehensive evaluation
    final_metrics = evaluator.run_qa_evaluation(
        qa_data=qa_data_with_predictions, llm_client=llm_client_for_eval
    )

    # --- Step 3: Print and Save Final Metrics ---
    print("\n--- Final Evaluation Metrics ---")
    print(json.dumps(final_metrics, indent=4, ensure_ascii=False))
    # Determine output summary filename based on input filename
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa_file", type=str, default="solver/data/res1.json")
    args = parser.parse_args()
    qa_file = os.path.join(dir_path, args.qa_file)

    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(final_metrics, f, ensure_ascii=False, indent=4)
