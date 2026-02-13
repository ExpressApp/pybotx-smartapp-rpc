from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RPCArgsBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class RPCRequest(BaseModel):
    method: str
    type: Literal["smartapp_rpc"]
    params: dict[str, Any] = Field(default_factory=dict)
