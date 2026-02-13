from collections.abc import Awaitable, Callable
from typing import TypeVar

from pybotx_smartapp_rpc.models.request import RPCArgsBaseModel
from pybotx_smartapp_rpc.models.responses import RPCErrorResponse, RPCResultResponse
from pybotx_smartapp_rpc.smartapp import SmartApp

RPCResponse = RPCErrorResponse | RPCResultResponse

TArgs = TypeVar("TArgs", bound=RPCArgsBaseModel)

HandlerWithArgs = Callable[[SmartApp, TArgs], Awaitable[RPCResponse]]
HandlerWithoutArgs = Callable[[SmartApp], Awaitable[RPCResponse]]
Handler = HandlerWithArgs | HandlerWithoutArgs
Middleware = Callable[[SmartApp, TArgs, HandlerWithArgs], Awaitable[RPCResponse]]

TException = TypeVar("TException", bound=Exception)
ExceptionHandler = Callable[[TException, SmartApp], Awaitable[RPCErrorResponse]]
ExceptionHandlerDict = dict[type[Exception], ExceptionHandler]
