from typing import Callable
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pybotx import SmartAppEvent

from pybotx_smartapp_rpc import (
    HandlerWithArgs,
    RPCArgsBaseModel,
    RPCResponse,
    RPCResultResponse,
    RPCRouter,
    SmartApp,
    SmartAppRPC,
)
from pybotx_smartapp_rpc.typing import Middleware


@pytest.fixture
def middleware_factory() -> Callable[..., Middleware]:
    def factory(middleware_number: int) -> Middleware:
        async def middleware(
            smartapp: SmartApp,
            rpc_arguments: RPCArgsBaseModel,
            call_next: HandlerWithArgs,
        ) -> RPCResponse:
            if not hasattr(smartapp.state, "middleware_order"):
                smartapp.state.middleware_order = []

            smartapp.state.middleware_order.append(middleware_number)

            return await call_next(smartapp, rpc_arguments)

        return middleware

    return factory


async def test_middleware_order(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
    middleware_factory: Callable[..., Middleware],
) -> None:
    # - Arrange -
    other_rpc = RPCRouter(middlewares=[middleware_factory(3), middleware_factory(4)])
    rpc = RPCRouter(middlewares=[middleware_factory(5), middleware_factory(6)])

    middleware_order = []

    @rpc.method(
        "get_api_version",
        middlewares=[middleware_factory(7), middleware_factory(8)],
    )
    async def get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        nonlocal middleware_order
        middleware_order = smartapp.state.middleware_order
        return RPCResultResponse(result=1)

    other_rpc.include_router(rpc)
    smartapp_rpc = SmartAppRPC(
        routers=[rpc],
        middlewares=[middleware_factory(1), middleware_factory(2)],
    )

    # - Act -
    await smartapp_rpc.handle_smartapp_event(
        smartapp_event_factory("get_api_version"),
        bot,
    )

    # - Assert -
    assert len(bot.method_calls) == 1
    bot.send_smartapp_event.assert_awaited_once_with(
        bot_id=bot_id,
        chat_id=chat_id,
        ref=ref,
        files=[],
        data={"status": "ok", "result": 1, "type": "smartapp_rpc"},
    )

    assert middleware_order == [1, 2, 3, 4, 5, 6, 7, 8]
