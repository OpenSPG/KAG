from pydantic import Field
from kag.common.llm.config.base import LLMConfig


class VLLMConfig(LLMConfig):
    model: str = Field(
        description="model name."
    )
    base_url: str = Field(
        description="post url."
    )