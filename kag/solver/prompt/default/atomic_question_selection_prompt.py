import logging
import re
from typing import List

from kag.interface import PromptABC
from kag.solver.logic.core_modules.common.one_hop_graph import (
    AtomRetrievalInfo
)

logger = logging.getLogger(__name__)


@PromptABC.register("atomic_question_selection_prompt")
class AtomicQuestionSelectionPrompt(PromptABC):
    template_zh = f"""# 任务
 你的任务是分析所提供的问题的上下文，从给定的问题列表中选择一个对回答指定问题最有帮助，最相关的子问题。避免选择根据给定上下文或你自己的知识已经可以回答的子问题。你只需要输出你觉得最合适的子问题，避免输出任何中间过程。
 
 # 输出格式
 请以以下 JSON 格式输出：
 {{
     "thinking": <A string. Your thinking for this selection task.>,
     "question_idx": <An integer, indicating a sub-question index from 1 to $num_atoms.>
 }}
 
 # 上下文
 我们已有的上下文：
 $chosen_context
 
 # 您可以选择的子问题
 $atom_list_str
 
 # 问题
 $content
 
 # 您的输出："""

    template_en = f"""# Task
  Your task is to analyze the context of the provided question and select a sub-question from the given list of questions that is the most helpful and relevant for answering the given question. Avoid choosing a sub-question that can already be answered based on the given context or your own knowledge. You only need to output the sub-question that you feel is most appropriate and avoid outputting any intermediate processes.
  
 # Output Format
 Please output in following JSON format:
 {{
     "thinking": <A string. Your thinking for this selection task.>,
     "question_idx": <An integer, indicating a sub-question index from 1 to $num_atoms.>
 }}
 
 # Context
 The context we already have:
 $chosen_context
 
 # Sub-Questions You Can Choose From
 $aq_list_str
 
 # Question
 $query
 
 # Your output:"""

    @property
    def template_variables(self) -> List[str]:
        return ["query", "num_atoms", "chosen_context", "aq_list_str"]

    def parse_response(self, rsp: str, **kwargs):
        if isinstance(rsp, str):
            try:
                rsp = json.loads(rsp.strip('```json').strip('```'))
            except Exception as e:
                print(f"[AtomQuestionSelectionParser] content to decode: {rsp}")
                print(f"Exception: {e}")
                return "", None
        try:
            thinking: str = rsp["thinking"]
            question_idx = rsp["question_idx"]
            if question_idx is not None and question_idx > 0:
                return thinking, question_idx
            else:
                return f"failure, {thinking}", None
        except Exception as e:
            print(f"[AtomQuestionSelectionParser] content to decode: {response}")
            print(f"Exception: {e}")
            return "", None

