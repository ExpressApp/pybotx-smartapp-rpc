from deepdiff import DeepDiff
from pydantic import BaseModel
from pydantic.v1.schema import get_model_name_map

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
)
from pybotx_smartapp_rpc.openapi.utils import (
    deep_dict_update,
)


class UserArgs(BaseModel):
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

    rpc_model_name_map = get_model_name_map(get_rpc_flat_models_from_routes(rpc))

    # - Act -
    path = get_rpc_openapi_path(
        method_name="get_api_version",
        route=rpc.rpc_methods["get_api_version"],
        model_name_map=rpc_model_name_map,
        security_scheme={"auth": []},
    )

    expected_path = {
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

    @rpc.method("get_user", errors=[UserNotFound], tags=["user"])
    async def get_api_version(
        smartapp: SmartApp, rpc_args: UserArgs
    ) -> RPCResultResponse[int]:
        return RPCResultResponse(result=42)

    smartapp_rpc = SmartAppRPC(routers=[rpc], errors=[OneUserNotFound])
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

    # expected_path = {
    #     "post": {
    #         "summary": "Get Api Version",
    #         "tags": ["rpc", "user"],
    #         "description": None,
    #         "operationId": "rpc_get_user",
    #         "requestBody": {
    #             "required": True,
    #             "content": {
    #                 "application/json": {
    #                     "schema": {
    #                         "properties": {"id": {"title": "Id", "type": "integer"}},
    #                         "required": ["id"],
    #                         "title": "UserArgs",
    #                         "type": "object",
    #                     }
    #                 }
    #             },
    #         },
    #         "responses": {
    #             200: {
    #                 "description": "Successful response. **result** field:",
    #                 "content": {
    #                     "application/json": {
    #                         "schema": {"title": "Response Get Api Version",
    #                                    "type": "integer"}
    #                     }
    #                 },
    #             },
    #             "UserNotFound": {
    #                 "description": "**Error**: Error description.",
    #                 "content": {
    #                     "application/json": {
    #                         "schema": {
    #                             "$defs": {
    #                                 "Meta": {
    #                                     "properties": {"user_id": {"title": "User Id",
    #                                                                "type": "integer"}},
    #                                     "required": ["user_id"],
    #                                     "title": "Meta",
    #                                     "type": "object",
    #                                 }
    #                             },
    #                             "description": "Error description.",
    #                             "properties": {
    #                                 "reason": {"default": "User not found in system",
    #                                            "title": "Reason", "type": "string"},
    #                                 "id": {"default": "UserNotFound", "title": "Id",
    #                                        "type": "string"},
    #                                 "meta": {"$ref": "#/$defs/Meta"},
    #                             },
    #                             "required": ["meta"],
    #                             "title": "UserNotFound",
    #                             "type": "object",
    #                         }
    #                     }
    #                 },
    #             },
    #             "OneUserNotFound": {
    #                 "description": "**Error**: User not found in system",
    #                 "content": {
    #                     "application/json": {
    #                         "schema": {
    #                             "$defs": {
    #                                 "Meta": {
    #                                     "properties": {"user_id": {"title": "User Id",
    #                                                                "type": "integer"}},
    #                                     "required": ["user_id"],
    #                                     "title": "Meta",
    #                                     "type": "object",
    #                                 }
    #                             },
    #                             "properties": {
    #                                 "reason": {"default": "User not found in system",
    #                                            "title": "Reason", "type": "string"},
    #                                 "id": {"default": "OneUserNotFound", "title": "Id",
    #                                        "type": "string"},
    #                                 "meta": {"$ref": "#/$defs/Meta"},
    #                             },
    #                             "required": ["meta"],
    #                             "title": "OneUserNotFound",
    #                             "type": "object",
    #                         }
    #                     }
    #                 },
    #             },
    #             "InvalidCredentialsError": {
    #                 "description": "**Error**: Invalid credentials",
    #                 "content": {
    #                     "application/json": {
    #                         "schema": {
    #                             "$defs": {
    #                                 "BaseModel": {"properties": {},
    #                                               "title": "BaseModel",
    #                                               "type": "object"}
    #                             },
    #                             "properties": {
    #                                 "reason": {"default": "Invalid credentials",
    #                                            "title": "Reason", "type": "string"},
    #                                 "id": {"default": "InvalidCredentialsError",
    #                                        "title": "Id", "type": "string"},
    #                                 "meta": {
    #                                     "anyOf": [
    #                                         {"additionalProperties": True,
    #                                          "type": "object"},
    #                                         {"$ref": "#/$defs/BaseModel"},
    #                                     ],
    #                                     "title": "Meta",
    #                                 },
    #                             },
    #                             "title": "InvalidCredentialsError",
    #                             "type": "object",
    #                         }
    #                     }
    #                 },
    #             },
    #         },
    #     },
    # }

    diff = DeepDiff(expected_path, path, ignore_order=True)
    assert not diff, diff


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
        "UserNotFound": {
            "description": "Error description.",
            "properties": {
                "id": {"default": "UserNotFound", "title": "Id", "type": "string"},
                "meta": {"$ref": "#/components/schemas/Meta"},
                "reason": {
                    "default": "User not found in " "system",
                    "title": "Reason",
                    "type": "string",
                },
            },
            "required": ["meta"],
            "title": "UserNotFound",
            "type": "object",
        },
    }

    diff = DeepDiff(expected_definitions, rpc_definitions, ignore_order=True)
    assert not diff, diff
