from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, TypeVar, Union

from pybotx import File
from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError

from pybotx_smartapp_rpc.models.errors import RPCError

_JsonableResultType = Union[float, int, str, bool, List, Dict]
JsonableResultType = TypeVar("JsonableResultType", bound=_JsonableResultType)

_ResultType = Union[BaseModel, _JsonableResultType]
ResultType = TypeVar("ResultType", bound=_ResultType)


class RPCResponseBaseModel(BaseModel):
    class Config:
        allow_population_by_field_name = True


@dataclass
class RPCResultResponse(Generic[ResultType]):
    result: ResultType
    files: List[File] = field(default_factory=list)
    encrypted: bool = True

    def jsonable_dict(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "type": "smartapp_rpc",
            "result": self.jsonable_result(),
        }

    def jsonable_result(self) -> JsonableResultType:
        if isinstance(self.result, BaseModel):
            return self.result.dict(by_alias=True)  # type: ignore

        return self.result  # type: ignore


@dataclass
class RPCErrorResponse:
    errors: List[RPCError]
    files: List[File] = field(default_factory=list)
    encrypted: bool = True

    def jsonable_dict(self) -> Dict[str, Any]:
        return {
            "status": "error",
            "type": "smartapp_rpc",
            "errors": self.jsonable_errors(),
        }

    def jsonable_errors(self) -> List[Dict[str, Any]]:
        return [error.dict() for error in self.errors]


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
                meta={"location": error["loc"]},
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
