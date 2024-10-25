from pydantic import Field
from kag.common.llm.config.base import LLMConfig


class OpenAIConfig(LLMConfig):
    api_key: str = Field(
        description="api key."
    )
    stream: bool = Field(
        description="if use stream mode",default=False
    )
    model: str = Field(
        description="model name."
    )
    temperature: float = Field(
        description="temperature.",default=0.7
    )
    base_url: str = Field(
        description="post url."
    )