from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pybotx import File
from pydantic import BaseModel, ConfigDict, ValidationError

from pybotx_smartapp_rpc.models.errors import RPCError

_JsonableResultType = float | int | str | bool | list[Any] | dict[str, Any]
JsonableResultType = TypeVar("JsonableResultType", bound=_JsonableResultType)

_ResultType = BaseModel | _JsonableResultType
ResultType = TypeVar("ResultType", bound=_ResultType)


class RPCResponseBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


@dataclass
class RPCResultResponse(Generic[ResultType]):
    result: ResultType
    files: list[File] = field(default_factory=list)
    encrypted: bool = True

    def jsonable_dict(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "type": "smartapp_rpc",
            "result": self.jsonable_result(),
        }

    def jsonable_result(self) -> _JsonableResultType:
        if isinstance(self.result, BaseModel):
            return self.result.model_dump(by_alias=True)

        return self.result


@dataclass
class RPCErrorResponse:
    errors: list[RPCError]
    files: list[File] = field(default_factory=list)
    encrypted: bool = True

    def jsonable_dict(self) -> dict[str, Any]:
        return {
            "status": "error",
            "type": "smartapp_rpc",
            "errors": self.jsonable_errors(),
        }

    def jsonable_errors(self) -> list[dict[str, Any]]:
        return [error.model_dump(by_alias=True) for error in self.errors]


def _normalize_error_id(error_type: str) -> str:
    if error_type.startswith("value_error") or error_type == "missing":
        return "VALUE_ERROR"

    if (
        error_type.startswith("type_error")
        or error_type.endswith("_parsing")
        or error_type.endswith("_type")
    ):
        return "TYPE_ERROR"

    return error_type.split(".")[0].upper()


def _normalize_error_message(error: Mapping[str, Any]) -> str:
    error_type = str(error["type"])

    if error_type == "missing":
        return "field required"

    if error_type in {"int_parsing", "int_type"}:
        return "value is not a valid integer"

    return str(error["msg"])


def build_invalid_rpc_request_error_response(
    exc: ValidationError,
) -> RPCErrorResponse:
    return RPCErrorResponse(
        errors=[
            RPCError(
                reason=f"Invalid RPC request: {_normalize_error_message(error)}",
                id=_normalize_error_id(str(error["type"])),
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
                reason=_normalize_error_message(error),
                id=_normalize_error_id(str(error["type"])),
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
