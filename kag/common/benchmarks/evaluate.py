
from typing import List

from .evaUtils import get_em_f1


class Evaluate():

    """
    provide evaluation for benchmarks, such as em、f1、answer_similarity, answer_correctness
    """
    def __init__(self, embedding_factory = "text-embedding-ada-002"):
        self.embedding_factory = embedding_factory

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
        return 0.0


    def getBenchMark(self, predictionlist: List[str], goldlist: List[str]):
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
        total_metrics = {'em': 0.0, 'f1': 0.0, 'answer_similarity': 0.0}
        
        # Iterate over prediction and gold lists to calculate EM and F1 scores
        for prediction, gold in zip(predictionlist, goldlist):
            em, f1 = get_em_f1(prediction, gold)  # Call external function to calculate EM and F1
            total_metrics['em'] += em  # Accumulate EM score
            total_metrics['f1'] += f1  # Accumulate F1 score
        
        # Calculate average EM and F1 scores
        total_metrics['em'] /= len(predictionlist)
        total_metrics['f1'] /= len(predictionlist)
        
        # Call method to calculate answer similarity
        total_metrics['answer_similarity'] = self.evaForSimilarity(predictionlist, goldlist)

        # Return evaluation metrics dictionary
        return total_metrics

