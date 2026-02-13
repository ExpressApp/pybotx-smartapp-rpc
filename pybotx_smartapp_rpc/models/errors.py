from typing import Any

from pydantic import BaseModel, Field


class RPCError(BaseModel):
    reason: str
    id: str
    meta: dict[str, Any] = Field(default_factory=dict)
