from typing import Any, Dict

from pydantic import BaseModel, Field


class RPCError(BaseModel):
    reason: str
    id: str
    meta: Dict[str, Any] = Field(default_factory=dict)
