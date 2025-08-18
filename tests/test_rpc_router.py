

import pytest

from pybotx_smartapp_rpc import RPCResultResponse, RPCRouter, SmartApp


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
