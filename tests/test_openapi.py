from enum import Enum
from typing import Any

import pytest
from deepdiff import DeepDiff
from pydantic import BaseModel

from pybotx_smartapp_rpc import (
    RPCError,
    RPCResultResponse,
    RPCRouter,
    SmartApp,
    SmartAppRPC,
)
from pybotx_smartapp_rpc.openapi.openapi import (
    get_rpc_flat_models_from_routes,
    get_rpc_model_definitions,
    get_rpc_openapi_path,
    update_fastapi_paths_by_rpc_router,
)
from pybotx_smartapp_rpc.openapi.utils import (
    deep_dict_update,
    get_model_name_map,
)


class UserArgs(BaseModel):
    id: int


class Response(BaseModel):
    result: int


class Meta(BaseModel):
    user_id: int


class Color(str, Enum):
    RED = "RED"
    GREEN = "GREEN"


class Status(Enum):
    OK = 1
    FAIL = 2


class Item(BaseModel):
    color: Color


class UserNotFoundError(RPCError):
    """Error description."""

    id: str = "UserNotFoundError"
    reason: str = "User not found in system"
    meta: Meta


class OneUserNotFoundError(UserNotFoundError):
    id: str = "OneUserNotFoundError"


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

    assert flat_rpc_models == {Response, UserArgs}  # type: ignore


async def test_flat_models_with_return_type() -> None:
    rpc = RPCRouter(tags=["test"])

    @rpc.method("method", return_type=Response)
    async def hidden(smartapp: SmartApp, rpc_args: UserArgs) -> RPCResultResponse[Meta]:
        return RPCResultResponse(Meta(user_id=1))

    flat_rpc_models = get_rpc_flat_models_from_routes(rpc)

    assert flat_rpc_models == {Response, UserArgs}  # type: ignore


async def test_get_rpc_openapi_path__without_args() -> None:
    # - Arrange -
    rpc = RPCRouter()

    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        return RPCResultResponse(result=1)

    rpc_model_name_map = get_model_name_map(get_rpc_flat_models_from_routes(rpc))

    # - Act -
    path = get_rpc_openapi_path(
        method_name="get_api_version",
        route=rpc.rpc_methods["get_api_version"],
        model_name_map=rpc_model_name_map,
        security_scheme={"auth": []},
    )

    expected_path: dict[str, Any] = {
        "post": {
            "description": None,
            "operationId": "rpc_get_api_version",
            "responses": {
                200: {
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

    diff = DeepDiff(expected_path, path)

    assert not diff, diff


async def test_collect_rpc_method_exists__with_errors() -> None:
    # - Arrange -
    rpc = RPCRouter(tags=["rpc"], errors=[InvalidCredentialsError])

    @rpc.method("get_user", errors=[UserNotFoundError], tags=["user"])
    async def get_api_version(
        smartapp: SmartApp, rpc_args: UserArgs
    ) -> RPCResultResponse[int]:
        return RPCResultResponse(result=42)

    smartapp_rpc = SmartAppRPC(routers=[rpc], errors=[OneUserNotFoundError])
    rpc_model_name_map = get_model_name_map(
        get_rpc_flat_models_from_routes(smartapp_rpc.router)
    )

    # - Act -
    path = get_rpc_openapi_path(
        method_name="get_user",
        route=rpc.rpc_methods["get_user"],
        model_name_map=rpc_model_name_map,
    )

    expected_path = {
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
                200: {
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
                "UserNotFoundError": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/UserNotFoundError"}
                        }
                    },
                    "description": "**Error**: Error description.",
                },
                "OneUserNotFoundError": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/OneUserNotFoundError"
                            }
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

    diff = DeepDiff(expected_path, path, ignore_order=True)
    assert not diff, diff


async def test_get_rpc_model_definition() -> None:
    # - Arrange -
    rpc = RPCRouter(tags=["rpc"])

    @rpc.method("get_user", errors=[UserNotFoundError], tags=["user"])
    async def get_api_version(
        smartapp: SmartApp, rpc_args: UserArgs
    ) -> RPCResultResponse[int]:
        return RPCResultResponse(result=42)

    smartapp_rpc = SmartAppRPC(routers=[rpc], errors=[])

    flat_rpc_models = get_rpc_flat_models_from_routes(smartapp_rpc.router)
    rpc_model_name_map = get_model_name_map(flat_rpc_models)

    # - Act -
    rpc_definitions = get_rpc_model_definitions(
        flat_models=flat_rpc_models, model_name_map=rpc_model_name_map
    )

    expected_definitions = {
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
        "UserNotFoundError": {
            "description": "Error description.",
            "properties": {
                "id": {"default": "UserNotFoundError", "title": "Id", "type": "string"},
                "meta": {"$ref": "#/components/schemas/Meta"},
                "reason": {
                    "default": "User not found in system",
                    "title": "Reason",
                    "type": "string",
                },
            },
            "required": ["meta"],
            "title": "UserNotFoundError",
            "type": "object",
        },
    }

    diff = DeepDiff(expected_definitions, rpc_definitions, ignore_order=True)
    assert not diff, diff


def test_update_fastapi_paths_adds_security_schemas_and_paths():
    # Arrange
    rpc = RPCRouter(tags=["rpc"])

    @rpc.method("get_user", errors=[UserNotFoundError], tags=["user"])
    async def get_user(smartapp: SmartApp, args: UserArgs) -> RPCResultResponse[int]:
        return RPCResultResponse(result=1)

    # pre-existing OpenAPI dict with unrelated path to ensure non-destructive merge
    openapi_dict = {
        "openapi": "3.1.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {"/health": {"get": {"responses": {"200": {"description": "ok"}}}}},
        "components": {"schemas": {"Existing": {"type": "object"}}},
    }

    security_definitions = {
        "RPC Auth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-RPC-AUTH",
            "description": "...",
        }
    }
    operation_security = {"RPC Auth": []}

    # Act
    update_fastapi_paths_by_rpc_router(
        openapi_dict,
        rpc_router=rpc,
        security_definitions=security_definitions,
        operation_security=operation_security,
    )

    # Assert: security schemes merged
    assert "components" in openapi_dict
    assert "securitySchemes" in openapi_dict["components"]
    assert openapi_dict["components"]["securitySchemes"]["RPC Auth"]["type"] == "apiKey"

    # Assert: new RPC path exists and has POST operation with security
    assert "/get_user" in openapi_dict["paths"]
    post_op = openapi_dict["paths"]["/get_user"]["post"]
    assert post_op["operationId"] == "rpc_get_user"
    assert {"RPC Auth": []} in post_op.get("security", [])

    # Request body should be present (because of args)
    assert post_op["requestBody"]["content"]["application/json"]

    # Responses include success and error codes by id
    responses = post_op["responses"]
    assert "200" in {
        str(k) for k in responses.keys()
    }  # numeric key 200 serialized later
    assert "UserNotFoundError" in responses
    # Error references use $ref to components/schemas
    err_schema = responses["UserNotFoundError"]["content"]["application/json"]["schema"]
    assert err_schema == {"$ref": "#/components/schemas/UserNotFoundError"}

    # Assert: schemas got updated with our models, while preserving existing schema
    schemas = openapi_dict["components"]["schemas"]
    assert "Existing" in schemas  # preserved
    # UserArgs schema present
    assert "UserArgs" in schemas
    # UserNotFound schema present and description trimmed
    assert "UserNotFoundError" in schemas
    assert schemas["UserNotFoundError"]["title"] == "UserNotFoundError"


def test_update_fastapi_paths_skips_hidden_and_handles_no_definitions():
    # Arrange
    rpc = RPCRouter()

    # method with primitive response, no args, included
    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        return RPCResultResponse(result=1)

    # method hidden from schema
    @rpc.method("__hidden_method", include_in_schema=False)
    async def hidden(smartapp: SmartApp, args: UserArgs) -> RPCResultResponse[int]:
        return RPCResultResponse(result=1)

    openapi_dict = {"openapi": "3.1.0", "info": {"title": "T", "version": "1"}}

    # Act
    update_fastapi_paths_by_rpc_router(openapi_dict, rpc)

    # Assert: only visible method path is added
    assert "/get_api_version" in openapi_dict["paths"]
    assert "/__hidden_method" not in openapi_dict["paths"]

    # Because only primitive types are involved, there should be no schemas added
    # The function adds schemas only if there are rpc_definitions
    components = openapi_dict.get("components", {})
    assert "schemas" not in components or components.get("schemas") == {}


def test_update_fastapi_paths_merges_into_existing_empty_sections_gracefully():
    # Arrange: empty containers
    rpc = RPCRouter()

    @rpc.method("ping")
    async def ping(smartapp: SmartApp) -> RPCResultResponse[str]:
        return RPCResultResponse(result="pong")

    # Existing dict without components/paths
    openapi_dict = {"openapi": "3.1.0", "info": {"title": "X", "version": "1"}}

    # Act
    update_fastapi_paths_by_rpc_router(openapi_dict, rpc)

    # Assert minimal structure created and path added
    assert "paths" in openapi_dict
    assert "/ping" in openapi_dict["paths"]



@pytest.mark.parametrize(
    "enum_cls, expected_type, expected_values",
    [
        (Color, "string", ["RED", "GREEN"]),
        (Status, "integer", [1, 2]),
    ],
)
def test_openapi_definitions_for_enums(enum_cls, expected_type, expected_values):
    defs = get_rpc_model_definitions(
        flat_models={enum_cls},
        model_name_map={enum_cls: enum_cls.__name__},
    )

    enum_schema = defs[enum_cls.__name__]
    assert enum_schema["enum"] == expected_values
    assert enum_schema["type"] == expected_type


def test_openapi_definitions_for_model_with_enum_field():
    defs = get_rpc_model_definitions(
        flat_models={Item, Color},
        model_name_map={Item: "Item", Color: "Color"},
    )

    assert "Color" in defs
    assert "Item" in defs

    item_schema = defs["Item"]
    assert item_schema["type"] == "object"
    props = item_schema["properties"]
    assert "color" in props
    # Убедимся, что поле color ссылается на определение Color
    assert "$ref" in props["color"]
    assert props["color"]["$ref"].endswith("/Color")
