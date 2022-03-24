from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Generic, List, TypeVar

from pybotx import File
from pydantic.error_wrappers import ValidationError

from pybotx_smartapp_rpc.models.errors import RPCError

ResultType = TypeVar("ResultType")


@dataclass
class RPCResultResponse(Generic[ResultType]):
    result: ResultType
    files: List[File] = field(default_factory=list)

    def jsonable_dict(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "type": "smartapp_rpc",
            "result": self.result,
        }


@dataclass
class RPCErrorResponse:
    errors: List[RPCError]
    files: List[File] = field(default_factory=list)

    def jsonable_dict(self) -> Dict[str, Any]:
        return {
            "status": "error",
            "type": "smartapp_rpc",
            "errors": [asdict(error) for error in self.errors],
        }


def build_invalid_rpc_request_error_response(
    exc: ValidationError,
) -> RPCErrorResponse:
    return RPCErrorResponse(
        errors=[
            RPCError(
                reason=f"Invalid RPC request: {error['msg']}",
                id=error["type"].split(".")[0].upper(),
                meta={"field": error["loc"][0]},
            )
            for error in exc.errors()
        ],
    )


def build_invalid_rpc_args_error_response(
    exc: ValidationError,
) -> RPCErrorResponse:
    return RPCErrorResponse(
        errors=[
            RPCError(
                reason=error["msg"],
                id=error["type"].split(".")[0].upper(),
                meta={"field": error["loc"][0]},
            )
            for error in exc.errors()
        ],
    )


def build_method_not_found_error_response(
    method: str,
) -> RPCErrorResponse:
    return RPCErrorResponse(
        errors=[
            RPCError(
                reason="Method not found",
                id="METHOD_NOT_FOUND",
                meta={"method": method},
            ),
        ],
    )
