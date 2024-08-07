from typing import List, Optional, Type

from pybotx import (
    Bot,
    BotAPISyncSmartAppEventErrorResponse,
    BotAPISyncSmartAppEventResponse,
    BotAPISyncSmartAppEventResultResponse,
    SmartAppEvent,
)
from pydantic import ValidationError

from pybotx_smartapp_rpc import RPCError, RPCErrorResponse
from pybotx_smartapp_rpc.exception_handlers import (
    default_exception_handler,
    rpc_exception_handler,
)
from pybotx_smartapp_rpc.exceptions import RPCErrorExc
from pybotx_smartapp_rpc.middlewares.exception_middleware import ExceptionMiddleware
from pybotx_smartapp_rpc.models.request import RPCRequest
from pybotx_smartapp_rpc.models.responses import (
    build_invalid_rpc_request_error_response,
)
from pybotx_smartapp_rpc.router import RPCRouter
from pybotx_smartapp_rpc.smartapp import SmartApp
from pybotx_smartapp_rpc.typing import ExceptionHandlerDict, Middleware, RPCResponse


class SmartAppRPC:
    def __init__(  # noqa: WPS234
        self,
        routers: List[RPCRouter],
        middlewares: Optional[List[Middleware]] = None,
        exception_handlers: Optional[ExceptionHandlerDict] = None,
        errors: Optional[List[Type[RPCError]]] = None,
    ) -> None:
        self._middlewares = middlewares or []
        self._insert_exception_middleware(exception_handlers or {})

        self._router = self._merge_routers(routers, errors or [])

    async def handle_smartapp_event(self, event: SmartAppEvent, bot: Bot) -> None:
        rpc_response: RPCResponse

        try:
            rpc_request = RPCRequest(**event.data)
        except ValidationError as invalid_rcp_request_exc:
            rpc_response = build_invalid_rpc_request_error_response(
                invalid_rcp_request_exc,
            )
        else:
            rpc_response = await self._router.perform_rpc_request(
                SmartApp(bot, event.bot.id, event.chat.id, event),
                rpc_request,
            )

        await bot.send_smartapp_event(
            bot_id=event.bot.id,
            chat_id=event.chat.id,
            data=rpc_response.jsonable_dict(),
            ref=event.ref,
            files=rpc_response.files,
            encrypted=rpc_response.encrypted,
        )

    async def handle_sync_smartapp_event(
        self,
        event: SmartAppEvent,
        bot: Bot,
    ) -> BotAPISyncSmartAppEventResponse:
        try:
            rpc_request = RPCRequest(**event.data)
        except ValidationError as invalid_rcp_request_exc:
            rpc_response: RPCResponse = build_invalid_rpc_request_error_response(
                invalid_rcp_request_exc,
            )
        else:
            rpc_response = await self._router.perform_rpc_request(
                SmartApp(bot, event.bot.id, event.chat.id, event),
                rpc_request,
            )

        if isinstance(rpc_response, RPCErrorResponse):
            return BotAPISyncSmartAppEventErrorResponse.from_domain(
                errors=rpc_response.jsonable_errors(),
            )

        return BotAPISyncSmartAppEventResultResponse.from_domain(
            data=rpc_response.jsonable_result(),
            files=rpc_response.files,
        )

    @property
    def router(self) -> RPCRouter:
        return self._router

    def _insert_exception_middleware(
        self,
        user_exception_handlers: ExceptionHandlerDict,
    ) -> None:
        exception_handlers: ExceptionHandlerDict = {
            Exception: default_exception_handler,
            RPCErrorExc: rpc_exception_handler,
        }
        exception_handlers.update(user_exception_handlers)
        exc_middleware = ExceptionMiddleware(exception_handlers)
        self._middlewares.insert(0, exc_middleware)

    def _merge_routers(
        self,
        routers: List[RPCRouter],
        errors: List[Type[RPCError]],
    ) -> RPCRouter:
        main_router = RPCRouter(middlewares=self._middlewares, errors=errors)
        main_router.include(*routers)

        return main_router
