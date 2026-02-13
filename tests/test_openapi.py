from enum import Enum

from pydantic import BaseModel, create_model

from pybotx_smartapp_rpc import (
    RPCArgsBaseModel,
    RPCError,
    RPCResultResponse,
    RPCRouter,
    SmartApp,
    SmartAppRPC,
)
from pybotx_smartapp_rpc.openapi_utils import (
    _extract_nested_models,
    deep_dict_update,
    get_rpc_flat_models_from_routes,
    get_rpc_model_definitions,
    get_rpc_model_name_map,
    get_rpc_openapi_path,
)


class UserArgs(RPCArgsBaseModel):
    id: int


class Response(BaseModel):
    result: int


class Meta(BaseModel):
    user_id: int


class UserNotFound(RPCError):
    """Error description."""

    id: str = "UserNotFound"
    reason: str = "User not found in system"
    meta: Meta


class OneUserNotFound(UserNotFound):
    id: str = "OneUserNotFound"


class InvalidCredentialsError(RPCError):
    id: str = "InvalidCredentialsError"
    reason: str = "Invalid credentials"


def test__deep_dict_update() -> None:
    a = {"a": {"b": {"c": 1}}}
    b = {"a": {"b": {"d": 2}}}
    deep_dict_update(a, b)

    assert a == {"a": {"b": {"c": 1, "d": 2}}}


async def test_flat_models() -> None:
    rpc = RPCRouter(tags=["test"])

    @rpc.method("method")
    async def hidden(
        smartapp: SmartApp, rpc_args: UserArgs
    ) -> RPCResultResponse[Response]:
        return RPCResultResponse(result=Response(result=1))

    @rpc.method("__hidden_method", include_in_schema=False)
    async def get_api_version(smartapp: SmartApp, args: Meta) -> RPCResultResponse[int]:
        return RPCResultResponse(result=1)

    flat_rpc_models = get_rpc_flat_models_from_routes(rpc)

    assert flat_rpc_models == {Response, UserArgs}


async def test_flat_models_with_return_type() -> None:
    rpc = RPCRouter(tags=["test"])

    @rpc.method("method", return_type=Response)
    async def hidden(smartapp: SmartApp, rpc_args: UserArgs) -> RPCResultResponse[Meta]:
        return RPCResultResponse(Meta(user_id=1))

    flat_rpc_models = get_rpc_flat_models_from_routes(rpc)

    assert flat_rpc_models == {Response, UserArgs}


async def test_get_rpc_openapi_path__without_args() -> None:
    # - Arrange -
    rpc = RPCRouter()

    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        return RPCResultResponse(result=1)

    rpc_model_name_map = get_rpc_model_name_map(get_rpc_flat_models_from_routes(rpc))

    # - Act -
    path = get_rpc_openapi_path(
        method_name="get_api_version",
        route=rpc.rpc_methods["get_api_version"],
        model_name_map=rpc_model_name_map,
        security_scheme={"auth": []},
    )

    assert path == {
        "post": {
            "description": None,
            "operationId": "rpc_get_api_version",
            "responses": {
                "ok": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "title": "Response Get Api Version",
                                "type": "integer",
                            }
                        }
                    },
                    "description": "Successful response. **result** field:",
                }
            },
            "summary": "Get Api Version",
            "security": [{"auth": []}],
        }
    }


async def test_collect_rpc_method_exists__with_errors() -> None:
    # - Arrange -
    rpc = RPCRouter(tags=["rpc"], errors=[InvalidCredentialsError])

    @rpc.method("get_user", errors=[UserNotFound], tags=["user"])
    async def get_api_version(
        smartapp: SmartApp, rpc_args: UserArgs
    ) -> RPCResultResponse[int]:
        return RPCResultResponse(result=42)

    smartapp_rpc = SmartAppRPC(routers=[rpc], errors=[OneUserNotFound])
    rpc_model_name_map = get_rpc_model_name_map(
        get_rpc_flat_models_from_routes(smartapp_rpc.router)
    )

    # - Act -
    path = get_rpc_openapi_path(
        method_name="get_user",
        route=rpc.rpc_methods["get_user"],
        model_name_map=rpc_model_name_map,
    )

    assert path == {
        "post": {
            "summary": "Get Api Version",
            "tags": ["rpc", "user"],
            "description": None,
            "operationId": "rpc_get_user",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/UserArgs"}
                    }
                },
            },
            "responses": {
                "ok": {
                    "description": "Successful response. **result** field:",
                    "content": {
                        "application/json": {
                            "schema": {
                                "title": "Response Get Api Version",
                                "type": "integer",
                            }
                        }
                    },
                },
                "UserNotFound": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/UserNotFound"}
                        }
                    },
                    "description": "**Error**: Error description.",
                },
                "OneUserNotFound": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OneUserNotFound"}
                        }
                    },
                    "description": "**Error**: User not found in system",
                },
                "InvalidCredentialsError": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/InvalidCredentialsError"
                            }
                        }
                    },
                    "description": "**Error**: Invalid credentials",
                },
            },
        }
    }


async def test_get_rpc_model_definition() -> None:
    # - Arrange -
    rpc = RPCRouter(tags=["rpc"])

    @rpc.method("get_user", errors=[UserNotFound], tags=["user"])
    async def get_api_version(
        smartapp: SmartApp, rpc_args: UserArgs
    ) -> RPCResultResponse[int]:
        return RPCResultResponse(result=42)

    smartapp_rpc = SmartAppRPC(routers=[rpc], errors=[])

    flat_rpc_models = get_rpc_flat_models_from_routes(smartapp_rpc.router)
    rpc_model_name_map = get_rpc_model_name_map(flat_rpc_models)

    # - Act -
    rpc_definitions = get_rpc_model_definitions(
        flat_models=flat_rpc_models, model_name_map=rpc_model_name_map
    )

    assert rpc_definitions == {
        "Meta": {
            "properties": {"user_id": {"title": "User Id", "type": "integer"}},
            "required": ["user_id"],
            "title": "Meta",
            "type": "object",
        },
        "UserArgs": {
            "properties": {"id": {"title": "Id", "type": "integer"}},
            "required": ["id"],
            "title": "UserArgs",
            "type": "object",
        },
        "UserNotFound": {
            "description": "Error description.",
            "properties": {
                "id": {"default": "UserNotFound", "title": "Id", "type": "string"},
                "meta": {"$ref": "#/components/schemas/Meta"},
                "reason": {
                    "default": "User not found in system",
                    "title": "Reason",
                    "type": "string",
                },
            },
            "required": ["meta"],
            "title": "UserNotFound",
            "type": "object",
        },
    }


async def test_flat_models_with_enum_and_any_response_type() -> None:
    class UserRole(str, Enum):
        ADMIN = "admin"

    class ArgsWithEnum(RPCArgsBaseModel):
        role: UserRole

    rpc = RPCRouter()

    @rpc.method("typed")
    async def typed_handler(
            smartapp: SmartApp,
            rpc_args: ArgsWithEnum,
    ) -> RPCResultResponse[int]:
        return RPCResultResponse(result=1)

    @rpc.method("untyped")
    async def untyped_handler(smartapp: SmartApp):
        return RPCResultResponse(result=1)

    flat_rpc_models = get_rpc_flat_models_from_routes(rpc)

    assert ArgsWithEnum in flat_rpc_models
    assert UserRole in flat_rpc_models


def test_get_rpc_model_name_map_with_duplicate_names() -> None:
    first_duplicate_model = create_model("DuplicatedModel", first=(int, ...))
    second_duplicate_model = create_model("DuplicatedModel", second=(int, ...))

    model_name_map = get_rpc_model_name_map(
        {first_duplicate_model, second_duplicate_model},
    )

    assert set(model_name_map.values()) == {"DuplicatedModel", "DuplicatedModel_1"}


def test_get_rpc_model_definitions_with_enum() -> None:
    class UserRole(str, Enum):
        ADMIN = "admin"
        USER = "user"

    flat_rpc_models = {UserRole}
    rpc_model_name_map = get_rpc_model_name_map(flat_rpc_models)

    rpc_definitions = get_rpc_model_definitions(
        flat_models=flat_rpc_models,
        model_name_map=rpc_model_name_map,
    )

    assert rpc_definitions["UserRole"] == {
        "enum": ["admin", "user"],
        "title": "UserRole",
        "type": "string",
    }


def test_extract_nested_models_with_non_class_annotation() -> None:
    assert _extract_nested_models("not_class_annotation") == set()
