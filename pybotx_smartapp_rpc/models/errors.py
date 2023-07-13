from typing import Any, Dict, Union

from pydantic import BaseModel, Field


class RPCError(BaseModel):
    reason: str
    id: str
    meta: Union[Dict[str, Any], BaseModel] = Field(default_factory=dict)
