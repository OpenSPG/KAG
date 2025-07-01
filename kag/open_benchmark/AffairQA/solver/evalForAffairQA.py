import logging
import os
import json
import re
import argparse
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any


from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.common.benchmarks.evaluate import Evaluate
from kag.interface.common.llm_client import LLMClient

logger = logging.getLogger(__name__)


# Assuming extract_answer_from_prediction is defined somewhere accessible
# or we define a simple version here if needed.
# For now, let's assume it's available or we just use the raw prediction.
def extract_answer_from_prediction(prediction: str) -> str:
    """
    Placeholder: Extracts answer from prediction string.
    """
    # Implement the actual logic if needed, e.g., splitting by "Answer:"
    if isinstance(prediction, str) and "答案:" in prediction:
        # Handle case where prediction might have thought process
        parts = prediction.split("答案:")
        if len(parts) > 1:
            return parts[-1].strip()
    # Fallback to return the raw prediction if format is unexpected
    return str(prediction).strip()


class AffairQAEvaluate(Evaluate):
    def _process_item(self, item: Dict[str, Any]):
        """Helper function to process a single QA item."""
        if "prediction" not in item or item["prediction"] is None:
            logger.warning(
                f"ID {item.get('id', 'N/A')} missing prediction, skipping evaluation."
            )
            return None
        if "answer" not in item or item["answer"] is None:
            logger.warning(
                f"ID {item.get('id', 'N/A')} missing answer, skipping evaluation."
            )
            return None
        if "question" not in item or item["question"] is None:
            logger.warning(
                f"ID {item.get('id', 'N/A')} missing question, skipping evaluation."
            )
            return None

        question = item["question"]
        prediction_extracted = extract_answer_from_prediction(item["prediction"])
        ans = item["answer"]
        gold_answer = str(ans[0]) if isinstance(ans, list) else str(ans)
        return question, prediction_extracted, gold_answer

    def run_affair_qa_evaluation(
        self, qa_data: List[Dict[str, Any]], llm_client: LLMClient
    ) -> Dict[str, Any]:
        """
        Runs the complete evaluation for AffairQA data using inherited Evaluate methods.
        Expects qa_data to contain 'question', 'prediction', 'answer'.
        """
        logger.info(f"Starting comprehensive evaluation for {len(qa_data)} QA pairs.")

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(self._process_item, qa_data))

        processed_results = [r for r in results if r is not None]

        if not processed_results:
            logger.error("No valid predictions found to evaluate.")
            return {"error": "No valid data for evaluation"}

        questions, predictions_extracted, gold_answers = zip(*processed_results)

        # --- Calculate Metrics using inherited methods ---
        logger.info("Calculating EM/F1 metrics...")
        em_f1_sim_metrics = self.getBenchMark(
            list(questions), list(predictions_extracted), list(gold_answers)
        )

        # --- Aggregate Results ---
        final_results = em_f1_sim_metrics

        logger.info(f"Comprehensive evaluation completed. Results: {final_results}")
        return final_results


def get_next_result_filename(base_path):
    """
    Check if result file exists and automatically increment the number.
    Example: if res8.json exists, return res9.json
    """
    dir_path = os.path.dirname(base_path)
    base_name = os.path.basename(base_path)
    match = re.match(r"res(\d+)\.json", base_name)
    if not match:
        # If it doesn't match res<number>.json, return original path
        logger.warning(
            f"Base path {base_path} does not match 'res<number>.json' pattern."
        )
        return base_path
    current_num = int(match.group(1))
    new_num = current_num
    new_path = os.path.join(dir_path, f"res{new_num}.json")
    while os.path.exists(new_path):
        new_num += 1
        new_path = os.path.join(dir_path, f"res{new_num}.json")
    if new_num > current_num:
        logger.info(
            f"Result file {base_name} exists. Using next available name: res{new_num}.json"
        )
    return new_path


if __name__ == "__main__":
    # Setup: Import executors and get base directory
    dir_path = os.path.dirname(os.path.abspath(__file__))
    import_modules_from_path(dir_path)  # Important for registering components

    # --- Argument Parsing for Input File ---
    parser = argparse.ArgumentParser(description="Evaluate AffairQA results.")
    parser.add_argument(
        "--input_file",
        type=str,
        default=os.path.join(dir_path, "data/res18.json"),  # Default input
        help="Path to the input JSON file containing questions, answers, and predictions (e.g., res1.json).",
    )
    args = parser.parse_args()
    input_results_file = args.input_file

    logger.info(f"Starting evaluation using input file: {input_results_file}")

    # --- Step 1: Load Existing Data with Predictions ---
    if not os.path.exists(input_results_file):
        logger.error(
            f"Input file not found: {input_results_file}. Cannot perform evaluation."
        )
        exit(1)  # Exit if input file doesn't exist

    try:
        with open(input_results_file, "r", encoding="utf-8") as f:
            qa_data_with_predictions = json.load(f)
        logger.info(
            f"Successfully loaded {len(qa_data_with_predictions)} records from {input_results_file}."
        )
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from input file {input_results_file}: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"Error loading data from {input_results_file}: {e}")
        exit(1)

    # --- Step 2: Perform Comprehensive Evaluation ---
    if not qa_data_with_predictions:
        logger.error("Loaded data is empty. Skipping evaluation.")
    else:
        logger.info("Initializing evaluation components...")
        # Load LLM Client needed for evaluation consistency check
        try:
            llm_config = KAG_CONFIG.all_config["chat_llm"]
            llm_client_for_eval = LLMClient.from_config(llm_config)
            logger.info("LLM Client for evaluation loaded successfully.")
        except Exception as e:
            logger.error(
                f"Failed to load LLM Client for evaluation: {e}. LLM Consistency check will be skipped.",
                exc_info=True,
            )
            llm_client_for_eval = None

        # Instantiate the evaluator
        evaluator = AffairQAEvaluate()

        # Run the comprehensive evaluation
        logger.info("Running evaluation on loaded data...")
        final_metrics = evaluator.run_affair_qa_evaluation(
            qa_data=qa_data_with_predictions, llm_client=llm_client_for_eval
        )

        # --- Step 3: Print and Save Final Metrics ---
        print("\n--- Final Evaluation Metrics ---")
        # Pretty print the dictionary
        print(json.dumps(final_metrics, indent=4, ensure_ascii=False))

        # Determine output summary filename based on input filename
        input_basename = os.path.basename(input_results_file)
        summary_filename = input_basename.replace("res", "evaluation_summary_").replace(
            ".json", ".json"
        )
        # Ensure summary is saved in the same directory as the input file or a specific output dir
        output_dir = os.path.dirname(input_results_file)
        summary_file_path = os.path.join(output_dir, summary_filename)

        try:
            with open(summary_file_path, "w", encoding="utf-8") as f:
                json.dump(final_metrics, f, ensure_ascii=False, indent=4)
            logger.info(f"Evaluation summary saved to {summary_file_path}")
        except IOError as e:
            logger.error(f"Failed to save evaluation summary: {e}")

    logger.info("Evaluation script finished.")
