from dataclasses import dataclass
from functools import partial
from typing import List, Optional, Type

from pybotx_smartapp_rpc.smartapp import SmartApp
from pybotx_smartapp_rpc.typing import (
    Handler,
    HandlerWithArgs,
    Middleware,
    RPCArgsBaseModel,
    RPCResponse,
)


@dataclass
class RPCMethod:
    handler: Handler
    middlewares: List[Middleware]
    arguments_class: Optional[Type[RPCArgsBaseModel]] = None

    async def __call__(
        self,
        smartapp: SmartApp,
        rpc_args: RPCArgsBaseModel,
    ) -> RPCResponse:
        # loop in reverse order
        # if middlewares = [m1, m2] and method.middlewares = [m3, m4]
        # then stack will be m1(m2(m3(m4(handler()))))
        handler: HandlerWithArgs = self.handler  # type: ignore
        for middleware in self.middlewares[::-1]:
            part = partial(middleware, call_next=handler)
            handler = part

        return await handler(smartapp, rpc_args)
