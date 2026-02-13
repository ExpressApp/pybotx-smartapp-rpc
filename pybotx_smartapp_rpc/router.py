import inspect
from collections.abc import Callable
from enum import Enum
from typing import Any, get_args, get_origin

from pydantic import ValidationError

from pybotx_smartapp_rpc.empty_args import EmptyArgs
from pybotx_smartapp_rpc.middlewares.empty_args_middleware import empty_args_middleware
from pybotx_smartapp_rpc.models.errors import RPCError
from pybotx_smartapp_rpc.models.method import RPCMethod
from pybotx_smartapp_rpc.models.request import RPCArgsBaseModel, RPCRequest
from pybotx_smartapp_rpc.models.responses import (
    ResultType,
    RPCResultResponse,
    build_invalid_rpc_args_error_response,
    build_method_not_found_error_response,
)
from pybotx_smartapp_rpc.smartapp import SmartApp
from pybotx_smartapp_rpc.typing import Handler, Middleware, RPCResponse


class RPCRouter:
    def __init__(
        self,
            middlewares: list[Middleware] | None = None,
            tags: list[str | Enum] | None = None,
        include_in_schema: bool = True,
            errors: list[type[RPCError]] | None = None,
    ) -> None:
        self.rpc_methods: dict[str, RPCMethod] = {}
        self.middlewares: list[Middleware] = middlewares or []
        self.tags: list[str | Enum] = tags or []
        self.include_in_schema = include_in_schema
        self.errors: list[type[RPCError]] = errors or []

    def method(
        self,
        rpc_method_name: str,
            middlewares: list[Middleware] | None = None,
            return_type: type[ResultType] | None = None,
            tags: list[str | Enum] | None = None,
            errors: list[type[RPCError]] | None = None,
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
            arguments_model, response_type = self._get_args_and_return_type(
                handler,
                return_type,
            )
            errors_fields, errors_models = self._get_error_fields_and_models(
                self.errors + (errors or []),
            )

            self.rpc_methods[rpc_method_name] = RPCMethod(
                handler=handler,
                middlewares=method_and_router_middlewares,
                response_type=response_type,
                arguments_model=arguments_model,
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

        if rpc_method.arguments_model:
            try:
                args = rpc_method.arguments_model.model_validate(rpc_request.params)
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

        router_errors_fields, router_errors_models = self._get_error_fields_and_models(
            self.errors,
        )

        for rpc_method_name, rpc_method in router.rpc_methods.items():
            rpc_method.middlewares = self.middlewares + rpc_method.middlewares
            rpc_method.errors = {**router_errors_fields, **rpc_method.errors}
            rpc_method.errors_models = {
                **router_errors_models,
                **rpc_method.errors_models,
            }
            self.rpc_methods[rpc_method_name] = rpc_method

    def _get_args_and_return_type(
        self,
        handler: Handler,
            return_type: type[ResultType] | None = None,
    ) -> tuple[type[RPCArgsBaseModel] | None, Any]:
        signature = inspect.signature(handler)
        response_type = self._resolve_response_type(
            return_annotation=signature.return_annotation,
            return_type=return_type,
        )

        args_annotations = [arg.annotation for arg in signature.parameters.values()]
        if len(args_annotations) >= 2:
            args_annotation = args_annotations[1]
            if inspect.isclass(args_annotation) and issubclass(
                    args_annotation,
                    RPCArgsBaseModel,
            ):
                return args_annotation, response_type

        return None, response_type

    def _resolve_response_type(
            self,
            *,
            return_annotation: Any,
            return_type: type[ResultType] | None,
    ) -> Any:
        if return_type is not None:
            return return_type

        if return_annotation is inspect.Signature.empty:
            return Any

        if get_origin(return_annotation) is RPCResultResponse:
            response_args = get_args(return_annotation)
            if response_args:
                return response_args[0]

        return Any

    def _get_error_fields_and_models(
        self,
            errors: list[type[RPCError]] | None,
    ) -> tuple[dict[str, dict[str, str | None]], dict[str, type[RPCError]]]:
        errors_fields: dict[str, dict[str, str | None]] = {}
        errors_models: dict[str, type[RPCError]] = {}
        if not errors:
            return errors_fields, errors_models

        for error in errors:
            error_id = error.model_fields["id"].default
            if not isinstance(error_id, str) or not error_id:
                continue

            reason = error.model_fields["reason"].default
            description = inspect.cleandoc(error.__doc__) if error.__doc__ else reason
            errors_fields[error_id] = {"description": description}
            errors_models[error_id] = error

        return errors_fields, errors_models
