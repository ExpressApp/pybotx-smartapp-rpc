from typing import Callable
from unittest.mock import AsyncMock
from uuid import UUID

from pybotx import (
    BotAPISyncSmartAppEventErrorResponse,
    BotAPISyncSmartAppEventResultResponse,
    Document,
    Image,
    SmartAppEvent,
)
from pybotx.missing import Undefined
from pydantic import Field

from pybotx_smartapp_rpc import (
    RPCArgsBaseModel,
    RPCError,
    RPCErrorResponse,
    RPCResponseBaseModel,
    RPCResultResponse,
    RPCRouter,
    SmartApp,
    SmartAppRPC,
)


async def test_rpc_call_rpc_error_returned(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
) -> None:
    # - Arrange -
    rpc = RPCRouter()

    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCErrorResponse:
        return RPCErrorResponse(
            errors=[
                RPCError(reason="Api version undefined", id="UNDEFINED_API_VERSION"),
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
            ],
            "type": "smartapp_rpc",
        },
        encrypted=True,
    )


async def test_rpc_call_with_wrong_args(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
) -> None:
    # - Arrange -
    rpc = RPCRouter()

    class SumArgs(RPCArgsBaseModel):
        first: int
        second: int

    @rpc.method("sum")
    async def sum_handler(smartapp: SmartApp, args: SumArgs) -> RPCResultResponse[int]:
        return RPCResultResponse(result=args.first + args.second)

    smartapp_rpc = SmartAppRPC(routers=[rpc])

    # - Act -
    await smartapp_rpc.handle_smartapp_event(
        smartapp_event_factory("sum", params={"first": "abc", "third": 2}),
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
                    "reason": "value is not a valid integer",
                    "id": "TYPE_ERROR",
                    "meta": {"location": ("first",)},
                },
                {
                    "reason": "field required",
                    "id": "VALUE_ERROR",
                    "meta": {"location": ("second",)},
                },
            ],
            "type": "smartapp_rpc",
        },
        encrypted=True,
    )


async def test_rpc_call_method_not_found(
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
        return RPCResultResponse(result=1)

    smartapp_rpc = SmartAppRPC(routers=[rpc])

    # - Act -
    await smartapp_rpc.handle_smartapp_event(
        smartapp_event_factory("sum"),
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
                    "reason": "Method not found",
                    "id": "METHOD_NOT_FOUND",
                    "meta": {"method": "sum"},
                },
            ],
            "type": "smartapp_rpc",
        },
        encrypted=True,
    )


async def test_rpc_call_wrong_rpc_request(
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
        return RPCResultResponse(result=1)

    smartapp_rpc = SmartAppRPC(routers=[rpc])
    smartapp_event = smartapp_event_factory("sum")
    del smartapp_event.data["method"]

    # - Act -
    await smartapp_rpc.handle_smartapp_event(
        smartapp_event,
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
                    "reason": "Invalid RPC request: field required",
                    "id": "VALUE_ERROR",
                    "meta": {"field": "method"},
                },
            ],
            "type": "smartapp_rpc",
        },
        encrypted=True,
    )


async def test_rpc_call_without_args(
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
        return RPCResultResponse(result=1)

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
        data={"status": "ok", "result": 1, "type": "smartapp_rpc"},
        encrypted=True,
    )


async def test_rpc_call_with_args(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
) -> None:
    # - Arrange -
    rpc = RPCRouter()

    class SumArgs(RPCArgsBaseModel):
        first: int
        second: int

    @rpc.method("sum")
    async def sum_handler(smartapp: SmartApp, args: SumArgs) -> RPCResultResponse[int]:
        return RPCResultResponse(result=args.first + args.second)

    smartapp_rpc = SmartAppRPC(routers=[rpc])

    # - Act -
    await smartapp_rpc.handle_smartapp_event(
        smartapp_event_factory("sum", params={"first": 1, "second": 2}),
        bot,
    )

    # - Assert -
    assert len(bot.method_calls) == 1
    bot.send_smartapp_event.assert_awaited_once_with(
        bot_id=bot_id,
        chat_id=chat_id,
        ref=ref,
        files=[],
        data={"status": "ok", "result": 3, "type": "smartapp_rpc"},
        encrypted=True,
    )


async def test_rpc_call_acceptiong_and_returning_aliased_model(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
) -> None:
    # - Arrange -
    rpc = RPCRouter()

    class SumArgs(RPCArgsBaseModel):
        first_arg: int = Field(alias="firstArg")
        second_arg: int = Field(alias="secondArg")

    class SumResponse(RPCResponseBaseModel):
        call_result: int = Field(alias="callResult")

    @rpc.method("sum")
    async def sum_handler(
        smartapp: SmartApp,
        args: SumArgs,
    ) -> RPCResultResponse[SumResponse]:
        return RPCResultResponse(
            SumResponse(call_result=args.first_arg + args.second_arg),
        )

    smartapp_rpc = SmartAppRPC(routers=[rpc])

    # - Act -
    await smartapp_rpc.handle_smartapp_event(
        smartapp_event_factory("sum", params={"firstArg": 1, "secondArg": 2}),
        bot,
    )

    # - Assert -
    assert len(bot.method_calls) == 1
    bot.send_smartapp_event.assert_awaited_once_with(
        bot_id=bot_id,
        chat_id=chat_id,
        ref=ref,
        files=[],
        data={"status": "ok", "result": {"callResult": 3}, "type": "smartapp_rpc"},
        encrypted=True,
    )


async def test_rpc_call_with_files_return(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
    document: Document,
    image: Image,
) -> None:
    # - Arrange -
    rpc = RPCRouter()

    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCResultResponse[int]:
        return RPCResultResponse(result=1, files=[document, image])

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
        files=[document, image],
        data={"status": "ok", "result": 1, "type": "smartapp_rpc"},
        encrypted=True,
    )


async def test_handle_sync_smartapp_event_without_args(
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
        return RPCResultResponse(result=1)

    smartapp_rpc = SmartAppRPC(routers=[rpc])

    # - Act -
    response = await smartapp_rpc.handle_sync_smartapp_event(
        smartapp_event_factory("get_api_version"),
        bot,
    )

    # - Assert -
    assert response == BotAPISyncSmartAppEventResultResponse.from_domain(
        data=1,
        files=Undefined,
    )


async def test_handle_sync_smartapp_event_rpc_error_returned(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
) -> None:
    # - Arrange -
    rpc = RPCRouter()

    @rpc.method("get_api_version")
    async def get_api_version(smartapp: SmartApp) -> RPCErrorResponse:
        return RPCErrorResponse(
            errors=[
                RPCError(reason="Api version undefined", id="UNDEFINED_API_VERSION"),
            ],
        )

    smartapp_rpc = SmartAppRPC(routers=[rpc])

    # - Act -
    response = await smartapp_rpc.handle_sync_smartapp_event(
        smartapp_event_factory("get_api_version"),
        bot,
    )

    # - Assert -
    assert response == BotAPISyncSmartAppEventErrorResponse.from_domain(
        errors=[
            {
                "reason": "Api version undefined",
                "id": "UNDEFINED_API_VERSION",
                "meta": {},
            },
        ]
    )


async def test_handle_sync_smartapp_event_with_wrong_args(
    smartapp_event_factory: Callable[..., SmartAppEvent],
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    ref: UUID,
) -> None:
    # - Arrange -
    rpc = RPCRouter()

    class SumArgs(RPCArgsBaseModel):
        first: int
        second: int

    @rpc.method("sum")
    async def sum_handler(smartapp: SmartApp, args: SumArgs) -> RPCResultResponse[int]:
        return RPCResultResponse(result=args.first + args.second)

    smartapp_rpc = SmartAppRPC(routers=[rpc])

    # - Act -
    response = await smartapp_rpc.handle_sync_smartapp_event(
        smartapp_event_factory("sum", params={"first": "abc", "third": 2}),
        bot,
    )

    # - Assert -
    assert response == BotAPISyncSmartAppEventErrorResponse.from_domain(
        errors=[
            {
                "reason": "value is not a valid integer",
                "id": "TYPE_ERROR",
                "meta": {"location": ("first",)},
            },
            {
                "reason": "field required",
                "id": "VALUE_ERROR",
                "meta": {"location": ("second",)},
            },
        ]
    )


async def test_handle_sync_smartapp_event_wrong_rpc_request(
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
        return RPCResultResponse(result=1)

    smartapp_rpc = SmartAppRPC(routers=[rpc])
    smartapp_event = smartapp_event_factory("sum")
    del smartapp_event.data["method"]

    # - Act -
    response = await smartapp_rpc.handle_sync_smartapp_event(
        smartapp_event,
        bot,
    )

    # - Assert -
    assert response == BotAPISyncSmartAppEventErrorResponse.from_domain(
        errors=[
            {
                "reason": "Invalid RPC request: field required",
                "id": "VALUE_ERROR",
                "meta": {"field": "method"},
            },
        ]
    )
