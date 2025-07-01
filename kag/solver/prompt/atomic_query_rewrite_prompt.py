from typing import List

from kag.common.llm.llm_response_parser import parse_json
from kag.interface import PromptABC


@PromptABC.register("atomic_query_rewrite_prompt")
class AtomicQueryRewritePrompt(PromptABC):
    template_en = """
        # Task
        Your task is to analyze the input question and known context, and then rephrase the question to expand diversity and recall knowledge that can help you answer the question better..
        
        # Output Format
        Please output in following JSON format:
        {{
            "thinking": <A string. Your thinking for this task, including analysis to the question and the given context.>,
            "rewritten_queries": <A list of string. The rewritten_queries indicating what you need.>
        }}
        
        # Known Context
        The context we already have:
        $chosen_context
        
        # Question
        $content
        
        # Your Output:
        """.strip()

    template_zh = """
        你的任务是分析输入的问题和已知的上下文，然后改写问题以扩展多样性、生成实体、扩展实体全称等多种表达方式，以召回能够帮助你更好地回答问题的知识。

        # 输出格式
        请以以下 JSON 格式输出：
        {{
            "thinking": <一个字符串。你对此任务的思考，包括对问题和给定上下文的分析。>,
            "rewritten_queries": <一个字符串列表。改写问题表明你需要什么。>
        }}
        
        # 上下文
        我们已有的上下文：
        $chosen_context
        
        # 问题
        $content
        
        # 你的输出：
        """.strip()

    @property
    def template_variables(self) -> List[str]:
        return ["content", "chosen_context"]

    def parse_response(self, response: str, **kwargs):
        try:
            output = parse_json(response)

            thinking: str = output["thinking"]
            rewritten_queries = output["rewritten_queries"]
            return len(rewritten_queries) > 0, thinking, rewritten_queries
        except Exception as e:
            print(f"[AtomicQueryRewritePrompt] content to decode: {response}")
            print(f"Exception: {e}")
            return False, "", []
