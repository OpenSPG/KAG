from typing import List

from kag.interface import PromptABC


@PromptABC.register("default_chunk_summary")
class ChunkSummaryPrompt(PromptABC):

    template_zh = """你是一个AI助手，你的任务是为给定的文本片段内容生成摘要。

要求：使用给定内容相同的语言生成摘要，输出时不要带如“内容摘要”之类的前置提示。

文本片段内容：
$content
"""

    template_en = """You are an AI assistant. Your task is to generate summary for the given text chunk content.

Requirements: Use the same language of the input content to generate summary. Omit prompt prefix words such as "summary".

Content of the given text chunk:
$content
"""

    @property
    def template_variables(self) -> List[str]:
        return ["content"]

    def parse_response(self, response: str, **kwargs):
        try:
            response = response.strip()
            return response
        except Exception as e:
            print(e)
            return ""
