import logging

logger = logging.getLogger(__name__)


def judge_is_answered(sub_answer: str):
    return sub_answer and "i don't know" not in sub_answer.lower()