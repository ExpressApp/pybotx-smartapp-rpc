from loguru import logger

from pybotx_smartapp_rpc.exceptions import RPCErrorExc
from pybotx_smartapp_rpc.models.errors import RPCError
from pybotx_smartapp_rpc.models.responses import RPCErrorResponse
from pybotx_smartapp_rpc.smartapp import SmartApp


async def default_exception_handler(
    exc: Exception,
    smartapp: SmartApp,
) -> RPCErrorResponse:
    logger.exception(exc)
    return RPCErrorResponse(
        errors=[RPCError(reason="Internal error", id=exc.__class__.__name__.upper())],
    )


async def rpc_exception_handler(
    exc: RPCErrorExc,
    smartapp: SmartApp,
) -> RPCErrorResponse:
    return RPCErrorResponse(errors=exc.errors)
