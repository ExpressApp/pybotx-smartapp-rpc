from typing import cast

from pybotx_smartapp_rpc.empty_args import EmptyArgs
from pybotx_smartapp_rpc.smartapp import SmartApp
from pybotx_smartapp_rpc.typing import (
    Handler,
    HandlerWithArgs,
    HandlerWithoutArgs,
    RPCArgsBaseModel,
    RPCResponse,
)


async def empty_args_middleware(
    smartapp: SmartApp,
    rpc_arguments: RPCArgsBaseModel,
    call_next: Handler,
) -> RPCResponse:
    if isinstance(rpc_arguments, EmptyArgs):
        call_next = cast(HandlerWithoutArgs, call_next)
        return await call_next(smartapp)

    call_next = cast(HandlerWithArgs, call_next)
    return await call_next(smartapp, rpc_arguments)
