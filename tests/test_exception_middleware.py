from typing import Callable
from unittest.mock import AsyncMock
from uuid import UUID

from pybotx import SmartAppEvent

from pybotx_smartapp_rpc import (
    RPCError,
    RPCErrorExc,
    RPCResultResponse,
    RPCRouter,
    SmartApp,
    SmartAppRPC,
)
from pybotx_smartapp_rpc.models.responses import RPCErrorResponse


async def test_rpc_call_error_raised(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
) -> None:
    # - Arrange -
    rpc = RPCRouter()

    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        raise ValueError

    smartapp_rpc = SmartAppRPC(routers=[rpc])

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
        data={
            "status": "error",
            "errors": [{"reason": "Internal error", "id": "VALUEERROR", "meta": {}}],
            "type": "smartapp_rpc",
        },
    )


async def test_rpc_call_rpc_error_raised(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
) -> None:
    # - Arrange -
    rpc = RPCRouter()

    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        raise RPCErrorExc(
            RPCError(reason="Api version undefined", id="UNDEFINED_API_VERSION"),
        )

    smartapp_rpc = SmartAppRPC(routers=[rpc])

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
        data={
            "status": "error",
            "errors": [
                {
                    "reason": "Api version undefined",
                    "id": "UNDEFINED_API_VERSION",
                    "meta": {},
                },
            ],
            "type": "smartapp_rpc",
        },
    )


async def test_rpc_call_rpc_multiple_errors_raised(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
) -> None:
    # - Arrange -
    rpc = RPCRouter()

    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        raise RPCErrorExc(
            [
                RPCError(reason="Api version undefined", id="UNDEFINED_API_VERSION"),
                RPCError(reason="Internal error", id="UNKNOWN_ERROR"),
            ],
        )

    smartapp_rpc = SmartAppRPC(routers=[rpc])

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
        data={
            "status": "error",
            "errors": [
                {
                    "reason": "Api version undefined",
                    "id": "UNDEFINED_API_VERSION",
                    "meta": {},
                },
                {"reason": "Internal error", "id": "UNKNOWN_ERROR", "meta": {}},
            ],
            "type": "smartapp_rpc",
        },
    )


async def test_rpc_call_exception_handler_called(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
) -> None:
    # - Arrange -
    async def exception_handler(
        exc: RPCErrorExc,
        smartapp: SmartApp,
    ) -> RPCErrorResponse:
        return RPCErrorResponse(
            errors=[
                RPCError(
                    reason="Internal error",
                    id="UNKNOWN_ERROR",
                    meta={"from": "exception_handler"},
                ),
            ],
        )

    rpc = RPCRouter()

    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        raise ValueError

    smartapp_rpc = SmartAppRPC(
        routers=[rpc],
        exception_handlers={ValueError: exception_handler},
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
        data={
            "status": "error",
            "errors": [
                {
                    "reason": "Internal error",
                    "id": "UNKNOWN_ERROR",
                    "meta": {"from": "exception_handler"},
                },
            ],
            "type": "smartapp_rpc",
        },
    )


async def test_rpc_call_exception_handler_called_raises_error(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
) -> None:
    # - Arrange -
    async def bad_exception_handler(
        exc: RPCErrorExc,
        smartapp: SmartApp,
    ) -> RPCErrorResponse:
        raise RuntimeError

    rpc = RPCRouter()

    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        raise ValueError

    smartapp_rpc = SmartAppRPC(
        routers=[rpc],
        exception_handlers={ValueError: bad_exception_handler},
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
        data={
            "status": "error",
            "errors": [{"reason": "Internal error", "id": "RUNTIMEERROR", "meta": {}}],
            "type": "smartapp_rpc",
        },
    )
