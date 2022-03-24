from typing import Any, Dict, Literal

from pydantic import BaseModel


class RPCRequest(BaseModel):
    method: str
    type: Literal["smartapp_rpc"]
    params: Dict[str, Any] = {}
