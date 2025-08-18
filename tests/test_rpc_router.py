from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from pybotx_smartapp_rpc import RPCResultResponse, RPCRouter, SmartApp, \
    RPCArgsBaseModel, RPCError
from pybotx_smartapp_rpc.middlewares.empty_args_middleware import empty_args_middleware


async def test_collect_rpc_method_exists() -> None:
    # - Arrange -
    rpc = RPCRouter()

    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        return RPCResultResponse(result=1)

    # - Act -
    with pytest.raises(ValueError) as exc:

        @rpc.method("get_api_version")
        async def other_get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
            return RPCResultResponse(result=1)

    # - Assert -
    assert "get_api_version" in str(exc.value)
    assert "already registered" in str(exc.value)


async def test_include_router_with_method_exists() -> None:
    # - Arrange -
    rpc = RPCRouter()
    other_rpc = RPCRouter()

    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        return RPCResultResponse(result=1)

    @other_rpc.method("get_api_version")
    async def other_get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        return RPCResultResponse(result=1)

    # - Act -
    with pytest.raises(ValueError) as exc:
        rpc.include_router(other_rpc)

    # - Assert -
    assert "get_api_version" in str(exc.value)
    assert "already registered" in str(exc.value)


def test_middlewares_order():
    """Check the order in which mixed middlewares are stored
    Note - the last middleware is added automatically
    """


    router_middleware = AsyncMock()
    method_middleware = AsyncMock()


    rpc = RPCRouter(middlewares=[router_middleware])

    @rpc.method("test_method", middlewares=[method_middleware])
    async def test_method(smartapp):
        pass

    rpc_method = rpc.rpc_methods["test_method"]

    # Check the order of middlewares
    assert rpc_method.middlewares[0] is router_middleware
    assert rpc_method.middlewares[1] is method_middleware
    assert rpc_method.middlewares[-1] is empty_args_middleware

async def test_rpc_router_call_method_directly():
    rpc = RPCRouter()

    called = False

    @rpc.method("dummy")
    async def dummy_method(smartapp: SmartApp):
        nonlocal called
        called = True
        return RPCResultResponse(result=42)

    response = await rpc.rpc_methods["dummy"].handler(MagicMock())
    assert called
    assert response.result == 42

