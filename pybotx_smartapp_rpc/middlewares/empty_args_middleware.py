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
    """
    Middleware function to handle RPC arguments and route the call accordingly based on
    whether the arguments are of type `EmptyArgs` or not.

    :param smartapp: An instance of `SmartApp` representing.
    :param rpc_arguments: An instance of `RPCArgsBaseModel` containing the RPC arguments
        to be validated and passed to the next handler.
    :param call_next: A handler function that takes either `smartapp` alone or both
        `smartapp` and `rpc_arguments`, determined by the type of the RPC arguments.
    :return: An `RPCResponse` object resulting from calling the appropriate handler.
    """
    if isinstance(rpc_arguments, EmptyArgs):
        call_next = cast(HandlerWithoutArgs, call_next)
        return await call_next(smartapp)

    call_next = cast(HandlerWithArgs, call_next)
    return await call_next(smartapp, rpc_arguments)
