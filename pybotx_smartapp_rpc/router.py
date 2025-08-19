import inspect
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from pydantic.error_wrappers import ValidationError
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

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
from pybotx_smartapp_rpc.models.model_field import ModelField
from pybotx_smartapp_rpc.smartapp import SmartApp
from pybotx_smartapp_rpc.typing import Handler, Middleware, RPCResponse


class RPCRouter:
    def __init__(
        self,
        middlewares: Optional[List[Middleware]] = None,
        tags: Optional[List[Union[str, Enum]]] = None,
        include_in_schema: bool = True,
        errors: Optional[List[Type[RPCError]]] = None,
    ) -> None:
        self.rpc_methods: Dict[str, RPCMethod] = {}
        self.middlewares: List[Middleware] = middlewares or []
        self.tags: List[Union[str, Enum]] = tags or []
        self.include_in_schema = include_in_schema
        self.errors: List[Type[RPCError]] = errors or []

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
            arg_field, response_field = self._get_args_and_return_field(
                handler,
                return_type,
            )
            errors_fields, errors_models = self._get_error_fields_and_models(
                self.errors + (errors or []),
            )

            self.rpc_methods[rpc_method_name] = RPCMethod(
                handler=handler,
                middlewares=method_and_router_middlewares,
                response_field=response_field,
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

        errors_fields, errors_models = self._get_error_fields_and_models(self.errors)

        for rpc_method_name, rpc_method in router.rpc_methods.items():
            rpc_method.middlewares = self.middlewares + rpc_method.middlewares
            rpc_method.errors = {**errors_fields, **rpc_method.errors}
            rpc_method.errors_models = {**errors_models, **rpc_method.errors_models}
            self.rpc_methods[rpc_method_name] = rpc_method

    def _get_handler_request_argument_model(
        self, handler_signature: inspect.Signature
    ) -> Optional[ModelField]:
        args_annotations = [
            arg[1].annotation for arg in handler_signature.parameters.items()
        ]
        if len(args_annotations) >= 2:
            return self.create_model_field(
                name=str(args_annotations[1].__name__),
                type_=args_annotations[1],
            )
        return None

    def _get_handler_response_model(
        self,
        handler_signature: inspect.Signature,
        return_type: Optional[Type[ResultType]],
        name: str,
    ) -> Optional[ModelField]:

        if return_type:
            response_type = return_type
        else:
            return_annotation = handler_signature.return_annotation
            if hasattr(return_annotation, "__args__"):  # noqa: WPS421
                response_type = return_annotation.__args__[0]
            else:
                response_type = None

        return self.create_model_field(
            name=name,
            type_=response_type,
        )

    def _get_args_and_return_field(
        self,
        handler: Handler,
        return_type: Optional[Type[ResultType]] = None,
    ) -> Tuple[Optional[ModelField], ModelField]:
        signature = inspect.signature(handler)

        response_field = self._get_handler_response_model(
            signature, return_type, f"Response_{handler.__name__}"
        )
        arg_field = self._get_handler_request_argument_model(signature)

        return arg_field, response_field

    def _get_error_fields_and_models(
        self,
        errors: Optional[List[Type[RPCError]]],
    ) -> Tuple[dict, dict]:
        errors_fields: Dict[str, dict] = {}
        errors_models: Dict[str, ModelField] = {}
        if not errors:
            return errors_fields, errors_models

        errors_fields = {
            error.model_fields["id"].default: {
                "description": error.__doc__ or error.model_fields["reason"].default,
            }
            for error in errors
            if error.model_fields["id"].default
        }
        errors_models = {
            error.model_fields["id"].default: self.create_model_field(
                name=error.__name__, type_=error
            )
            for error in errors
            if error.model_fields["id"].default
        }

        return errors_fields, errors_models

    @staticmethod
    def create_model_field(
        name: str,
        type_: Any,
        default: Optional[Any] = PydanticUndefined,
        field_info: Optional[FieldInfo] = None,
        alias: Optional[str] = None,
    ) -> ModelField:
        field_info = field_info or FieldInfo(
            annotation=type_, default=default, alias=alias
        )
        return ModelField(name=name, field_info=field_info)
