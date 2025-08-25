from typing import Any, Dict, Literal

from pydantic import BaseModel


class RPCArgsBaseModel(BaseModel):
    model_config = {"populate_by_name": True}


class RPCRequest(BaseModel):
    method: str
    type: Literal["smartapp_rpc"]
    params: Dict[str, Any] = {}
