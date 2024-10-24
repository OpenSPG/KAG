"""LLM Parameters model."""

from pydantic import BaseModel, Field

import kag.common.llm.config.defaults as defs


class LLMConfig(BaseModel):
    """LLM Config model."""

