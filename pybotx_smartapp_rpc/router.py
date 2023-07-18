from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple, Type, Union

from pydantic import BaseConfig
from pydantic.error_wrappers import ValidationError
from pydantic.fields import ModelField

from pybotx_smartapp_rpc import RPCError
from pybotx_smartapp_rpc.empty_args import EmptyArgs
from pybotx_smartapp_rpc.middlewares.empty_args_middleware import empty_args_middleware
from pybotx_smartapp_rpc.models.method import RPCMethod
from pybotx_smartapp_rpc.models.request import RPCRequest
from pybotx_smartapp_rpc.models.responses import (
    ResultType,
    build_invalid_rpc_args_error_response,
    build_method_not_found_error_response,
)
from pybotx_smartapp_rpc.smartapp import SmartApp
from pybotx_smartapp_rpc.typing import Handler, Middleware, RPCResponse


class RPCRouter:
    def __init__(
        self,
        middlewares: Optional[List[Middleware]] = None,
        tags: Optional[List[Union[str, Enum]]] = None,
        include_in_schema: bool = True,
    ) -> None:
        self.rpc_methods: Dict[str, RPCMethod] = {}
        self.middlewares: List[Middleware] = middlewares or []
        self.tags: List[Union[str, Enum]] = tags or []
        self.include_in_schema = include_in_schema

    def method(
        self,
        rpc_method_name: str,
        middlewares: Optional[List[Middleware]] = None,
        return_type: Optional[Type[ResultType]] = None,
        tags: Optional[List[Union[str, Enum]]] = None,
        errors: Optional[List[Type[RPCError]]] = None,
        include_in_schema: bool = True,
    ) -> Callable[[Handler], Handler]:
        if rpc_method_name in self.rpc_methods:
            raise ValueError(f"RPC method {rpc_method_name} already registered!")

        method_and_router_middlewares = self.middlewares + (middlewares or [])
        method_and_router_middlewares += [empty_args_middleware]

        current_tags = self.tags.copy()
        if tags:
            current_tags.extend(tags)

        def decorator(handler: Handler) -> Handler:
            annotations = list(handler.__annotations__.values())
            arg_field: Optional[ModelField] = None
            if len(annotations) == 3:
                # __annotations__ contains args and return typing
                # so len 3 means that method has rpc args
                arg_field = ModelField(
                    name=f"Args_{rpc_method_name}",
                    type_=annotations[1],
                    model_config=BaseConfig,
                    class_validators={},
                )

            errors_fields, errors_models = self._get_error_fields_and_models(errors)

            self.rpc_methods[rpc_method_name] = RPCMethod(
                handler=handler,
                middlewares=method_and_router_middlewares,
                response_field=self._get_response_field(return_type, annotations),
                arguments_field=arg_field,
                tags=current_tags,
                errors=errors_fields,
                errors_models=errors_models,
                include_in_schema=include_in_schema and self.include_in_schema,
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

        if rpc_method.arguments_field:
            try:
                args = rpc_method.arguments_field.type_(**rpc_request.params)
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

    def _get_response_field(
        self,
        return_type: Optional[Type[ResultType]],
        annotations: list,
    ) -> ModelField:
        if return_type:
            response_type = return_type
        else:
            if hasattr(annotations[-1], "__args__"):  # noqa: WPS421
                response_type = annotations[-1].__args__[0]
            else:
                response_type = str  # type: ignore

        return ModelField(
            name=f"{response_type.__name__}",
            type_=response_type,
            model_config=BaseConfig,
            class_validators={},
        )

    def _get_error_fields_and_models(
        self,
        errors: Optional[List[Type[RPCError]]],
    ) -> Tuple[Optional[dict], dict]:
        errors_fields = {}
        errors_models = {}
        if errors:
            errors_fields = {
                error.__fields__["id"].default: {
                    "description": error.__fields__["reason"].default,
                }
                for error in errors
                if error.__fields__["id"].default
            }
            errors_models = {
                error.__fields__["id"].default: ModelField(
                    name=error.__name__,
                    type_=error,
                    class_validators=None,
                    model_config=BaseConfig,
                )
                for error in errors
                if error.__fields__["id"].default
            }

        return errors_fields, errors_models
