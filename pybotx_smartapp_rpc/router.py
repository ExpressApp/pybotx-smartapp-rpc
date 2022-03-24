from typing import Callable, Dict, List, Optional, Type

from pydantic.error_wrappers import ValidationError

from pybotx_smartapp_rpc.empty_args import EmptyArgs
from pybotx_smartapp_rpc.middlewares.empty_args_middleware import empty_args_middleware
from pybotx_smartapp_rpc.models.method import RPCMethod
from pybotx_smartapp_rpc.models.request import RPCRequest
from pybotx_smartapp_rpc.models.responses import (
    build_invalid_rpc_args_error_response,
    build_method_not_found_error_response,
)
from pybotx_smartapp_rpc.smartapp import SmartApp
from pybotx_smartapp_rpc.typing import (
    Handler,
    Middleware,
    RPCArgsBaseModel,
    RPCResponse,
)


class RPCRouter:
    def __init__(self, middlewares: Optional[List[Middleware]] = None) -> None:
        self.rpc_methods: Dict[str, RPCMethod] = {}
        self.middlewares: List[Middleware] = middlewares or []

    def method(
        self,
        rpc_method_name: str,
        middlewares: Optional[List[Middleware]] = None,
    ) -> Callable[[Handler], Handler]:
        if rpc_method_name in self.rpc_methods:
            raise ValueError(f"RPC method {rpc_method_name} already registered!")

        method_and_router_middlewares = self.middlewares + (middlewares or [])
        method_and_router_middlewares += [empty_args_middleware]

        def decorator(handler: Handler) -> Handler:
            annotations = list(handler.__annotations__.values())
            arguments_class: Optional[Type[RPCArgsBaseModel]] = None
            if len(annotations) == 3:
                # __annotations__ contains args and return typing
                # so len 3 means that method has rpc args
                arguments_class = annotations[1]

            self.rpc_methods[rpc_method_name] = RPCMethod(
                handler=handler,
                arguments_class=arguments_class,
                middlewares=method_and_router_middlewares,
            )

            return handler

        return decorator

    async def perform_rpc_request(
        self,
        smartapp: SmartApp,
        rpc_request: RPCRequest,
    ) -> RPCResponse:
        rpc_method = self.rpc_methods.get(rpc_request.method)
        if not rpc_method:
            return build_method_not_found_error_response(rpc_request.method)

        if rpc_method.arguments_class:
            try:
                args = rpc_method.arguments_class(**rpc_request.params)
            except ValidationError as invalid_rpc_args_exc:
                return build_invalid_rpc_args_error_response(invalid_rpc_args_exc)
        else:
            args = EmptyArgs()

        return await rpc_method(smartapp, args)

    def include(self, *routers: "RPCRouter") -> None:
        for router in routers:
            self.include_router(router)

    def include_router(self, router: "RPCRouter") -> None:
        already_exist_handlers = self.rpc_methods.keys() & router.rpc_methods.keys()
        if already_exist_handlers:
            raise ValueError(
                f"RPC methods {already_exist_handlers} already registered!",
            )

        for rpc_method_name, rpc_method in router.rpc_methods.items():
            rpc_method.middlewares = self.middlewares + rpc_method.middlewares
            self.rpc_methods[rpc_method_name] = rpc_method
