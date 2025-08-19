from typing import Sequence, Any

from fastapi.encoders import jsonable_encoder
from fastapi.openapi.models import OpenAPI
from fastapi.openapi.utils import get_openapi
from starlette.routing import BaseRoute

from pybotx_smartapp_rpc import RPCRouter
from pybotx_smartapp_rpc.fastapi_utils.security import RPCAuth, \
    get_openapi_security_definitions
from pybotx_smartapp_rpc.openapi.openapi import update_fastapi_paths_by_rpc_router


def rpc_openapi(
    *,
    title: str,
    version: str,
    fastapi_routes: Sequence[BaseRoute],
    rpc_router: RPCRouter,
    security:RPCAuth,
    **kwargs: Any,
) -> dict[str, Any]:
    openapi_dict = get_openapi(
        title=title,
        version=version,
        routes=fastapi_routes,
        **kwargs,
    )

    security_definitions, operation_security = get_openapi_security_definitions(
        security_component=security
    )

    update_fastapi_paths_by_rpc_router(openapi_dict,rpc_router,security_definitions,operation_security)

    return jsonable_encoder(OpenAPI(**openapi_dict), by_alias=True, exclude_none=True)
