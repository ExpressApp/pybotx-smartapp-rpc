from dataclasses import dataclass, field
from enum import Enum
from functools import partial
from typing import Dict, List, Optional, Union

from pydantic.fields import ModelField

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
    response_field: ModelField
    arguments_field: Optional[ModelField] = None
    tags: List[Union[str, Enum]] = field(default_factory=list)
    errors: Optional[Dict[str, dict]] = None
    errors_models: Optional[Dict[str, ModelField]] = None
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
            part = partial(middleware, call_next=handler)
            handler = part

        return await handler(smartapp, rpc_args)
