from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    type: Literal["text", "url", "image"]
    content: str = Field(min_length=1)
