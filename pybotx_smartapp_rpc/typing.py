from typing import Awaitable, Callable, Dict, Type, TypeVar, Union

from pybotx_smartapp_rpc.models.request import RPCArgsBaseModel
from pybotx_smartapp_rpc.models.responses import RPCErrorResponse, RPCResultResponse
from pybotx_smartapp_rpc.smartapp import SmartApp

RPCResponse = Union[RPCErrorResponse, RPCResultResponse]

TArgs = TypeVar("TArgs", bound=RPCArgsBaseModel)

HandlerWithArgs = Callable[[SmartApp, TArgs], Awaitable[RPCResponse]]
HandlerWithoutArgs = Callable[[SmartApp], Awaitable[RPCResponse]]
Handler = Union[HandlerWithArgs, HandlerWithoutArgs]
Middleware = Callable[[SmartApp, TArgs, HandlerWithArgs], Awaitable[RPCResponse]]

TException = TypeVar("TException", bound=Exception)
ExceptionHandler = Callable[[TException, SmartApp], Awaitable[RPCErrorResponse]]
ExceptionHandlerDict = Dict[Type[Exception], ExceptionHandler]
