from typing import Any, Dict, Literal

from pydantic import BaseModel


class RPCArgsBaseModel(BaseModel):
    class Config:
        allow_population_by_field_name = True


class RPCRequest(BaseModel):
    method: str
    type: Literal["smartapp_rpc"]
    params: Dict[str, Any] = {}
