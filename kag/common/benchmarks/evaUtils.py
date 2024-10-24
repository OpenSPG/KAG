import re
import string
from collections import Counter


def normalize_answer(s):
    """
    Normalizes the answer string.

    This function standardizes the answer string through a series of steps including removing articles,
    fixing whitespace, removing punctuation, and converting text to lowercase. This ensures consistency
    and fairness when comparing answers.

    Parameters:
    s (str): The answer string to be standardized.

    Returns:
    str: The standardized answer string.
    """
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)

    def white_space_fix(text):
        return ' '.join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)

    def lower(text):
        return str(text).lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def f1_score(prediction, ground_truth):
    """
    Calculates the F1 score between the predicted answer and the ground truth.

    The F1 score is the harmonic mean of precision and recall, used to evaluate the model's performance in question answering tasks.

    Parameters:
    prediction (str): The predicted answer from the model.
    ground_truth (str): The actual ground truth answer.

    Returns:
    tuple: A tuple containing the F1 score, precision, and recall.
    """

    normalized_prediction = normalize_answer(prediction)
    normalized_ground_truth = normalize_answer(ground_truth)

    ZERO_METRIC = (0, 0, 0)

    if normalized_prediction in ['yes', 'no', 'noanswer'] and normalized_prediction != normalized_ground_truth:
        return ZERO_METRIC

    if normalized_ground_truth in ['yes', 'no', 'noanswer'] and normalized_prediction != normalized_ground_truth:
        return ZERO_METRIC

    prediction_tokens = normalized_prediction.split()
    ground_truth_tokens = normalized_ground_truth.split()

    # Calculate the number of matching words between the predicted and ground truth answers
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())

    if num_same == 0:
        return ZERO_METRIC

    precision = 1.0 * num_same / len(prediction_tokens)
    recall = 1.0 * num_same / len(ground_truth_tokens)
    f1 = (2 * precision * recall) / (precision + recall)

    return f1, precision, recall


def exact_match_score(prediction, ground_truth):
    """
    Calculates the exact match score between a predicted answer and the ground truth answer.
    
    This function normalizes both the predicted answer and the ground truth answer before comparing them.
    Normalization is performed to ensure that non-essential differences such as spaces and case are ignored.
    
    Parameters:
    prediction (str): The predicted answer string.
    ground_truth (str): The ground truth answer string.
    
    Returns:
    int: 1 if the predicted answer exactly matches the ground truth answer, otherwise 0.
    """

    return 1 if normalize_answer(prediction) == normalize_answer(ground_truth) else 0

def get_em_f1(prediction, gold):
    """
    Calculates the Exact Match (EM) score and F1 score between the prediction and the gold standard.
    
    This function evaluates the performance of a model in text similarity tasks by calculating the EM score and F1 score to measure the accuracy of the predictions.
    
    Parameters:
    prediction (str): The output predicted by the model.
    gold (str): The gold standard output (i.e., the correct output).
    
    Returns:
    tuple: A tuple containing two floats, the EM score and the F1 score. The EM score represents the exact match accuracy, while the F1 score is a combination of precision and recall.
    """

    em = exact_match_score(prediction, gold)
    f1, precision, recall = f1_score(prediction, gold)
    
    return float(em), f1