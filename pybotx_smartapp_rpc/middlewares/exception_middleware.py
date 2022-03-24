from typing import Optional

from pybotx_smartapp_rpc.exception_handlers import default_exception_handler
from pybotx_smartapp_rpc.smartapp import SmartApp
from pybotx_smartapp_rpc.typing import (
    ExceptionHandler,
    ExceptionHandlerDict,
    HandlerWithArgs,
    RPCArgsBaseModel,
    RPCResponse,
)


class ExceptionMiddleware:
    def __init__(
        self,
        exception_handlers: Optional[ExceptionHandlerDict] = None,
    ) -> None:
        self._exception_handlers: ExceptionHandlerDict = exception_handlers or {}

    async def __call__(
        self,
        smartapp: SmartApp,
        rpc_arguments: RPCArgsBaseModel,
        call_next: HandlerWithArgs,
    ) -> RPCResponse:
        try:
            rpc_result = await call_next(smartapp, rpc_arguments)
        except Exception as exc:
            exception_handler = self._get_exception_handler(exc)
            try:  # noqa: WPS505
                return await exception_handler(exc, smartapp)
            except Exception as error_handler_exc:
                return await default_exception_handler(error_handler_exc, smartapp)

        return rpc_result

    def _get_exception_handler(self, exc: Exception) -> ExceptionHandler:
        for exc_cls in type(exc).mro():
            handler = self._exception_handlers.get(exc_cls)
            if handler:
                return handler

        raise RuntimeError("No handler for Exception found.")  # pragma: no cover
