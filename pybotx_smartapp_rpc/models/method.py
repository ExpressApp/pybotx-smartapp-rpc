from dataclasses import dataclass, field
from enum import Enum
from functools import partial
from typing import Any

from pybotx_smartapp_rpc.models.errors import RPCError
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
    middlewares: list[Middleware]
    response_type: Any
    arguments_model: type[RPCArgsBaseModel] | None = None
    tags: list[str | Enum] = field(default_factory=list)
    errors: dict[str, dict[str, str | None]] = field(default_factory=dict)
    errors_models: dict[str, type[RPCError]] = field(default_factory=dict)
    include_in_schema: bool = True

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
            part = partial(middleware, call_next=handler)  # type: ignore
            handler = part

        return await handler(smartapp, rpc_args)
