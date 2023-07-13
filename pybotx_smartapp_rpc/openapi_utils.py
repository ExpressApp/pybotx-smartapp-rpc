from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

from pydantic import BaseModel
from pydantic.fields import ModelField
from pydantic.schema import field_schema, get_flat_models_from_fields

from pybotx_smartapp_rpc import RPCRouter
from pybotx_smartapp_rpc.models.method import RPCMethod

REF_PREFIX = "#/components/schemas/"


def deep_dict_update(main_dict: Dict[Any, Any], update_dict: Dict[Any, Any]) -> None:
    for key in update_dict.keys():
        if (
            key in main_dict
            and isinstance(main_dict[key], dict)
            and isinstance(update_dict[key], dict)
        ):
            deep_dict_update(main_dict[key], update_dict[key])
        else:
            main_dict[key] = update_dict[key]


def get_rpc_flat_models_from_routes(
    router: RPCRouter,
) -> Set[Union[Type[BaseModel], Type[Enum]]]:
    body_fields_from_routes: List[ModelField] = []
    responses_from_routes: List[ModelField] = []

    for method_name in router.rpc_methods.keys():
        if not router.rpc_methods[method_name].include_in_schema:
            continue

        if router.rpc_methods[method_name].arguments_field:
            body_fields_from_routes.append(
                router.rpc_methods[method_name].arguments_field,  # type: ignore
            )
        if router.rpc_methods[method_name].response_field:
            responses_from_routes.append(router.rpc_methods[method_name].response_field)

        if router.rpc_methods[method_name].errors_models:
            responses_from_routes.extend(
                router.rpc_methods[method_name].errors_models.values(),  # type: ignore
            )

    return get_flat_models_from_fields(
        body_fields_from_routes + responses_from_routes,
        known_models=set(),
    )


def get_openapi_operation_rpc_args(
    *,
    body_field: Optional[ModelField],
    model_name_map: Dict[Union[Type[BaseModel], Type[Enum]], str],
) -> Optional[Dict[str, Any]]:
    if not body_field:
        return None

    body_schema, _, _ = field_schema(
        body_field,
        model_name_map=model_name_map,
        ref_prefix=REF_PREFIX,
    )
    request_media_type = "application/json"
    required = body_field.required
    request_body_oai: Dict[str, Any] = {}
    if required:
        request_body_oai["required"] = required

    request_media_content: Dict[str, Any] = {"schema": body_schema}
    request_body_oai["content"] = {request_media_type: request_media_content}
    return request_body_oai


def get_openapi_rpc_metadata(*, name: str, route: RPCMethod) -> Dict[str, Any]:
    operation: Dict[str, Any] = {}
    operation["summary"] = (
        route.handler.__name__.replace(".", " ").replace("_", " ").title()
    )
    operation["description"] = route.handler.__doc__
    operation[
        "operationId"
    ] = f"rpc_{name.replace('.', '_').replace(':', '_').replace('-', '_').lower()}"

    if route.tags:
        operation["tags"] = route.tags

    return operation


def get_rpc_openapi_path(
    *,
    method_name: str,
    route: RPCMethod,
    model_name_map: Dict[Union[Type[BaseModel], Type[Enum]], str],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Taken from FastAPI."""
    path = {}
    definitions: Dict[str, Any] = {}

    operation = get_openapi_rpc_metadata(name=method_name, route=route)

    request_body_oai = get_openapi_operation_rpc_args(
        body_field=route.arguments_field,
        model_name_map=model_name_map,
    )
    if request_body_oai:
        operation["requestBody"] = request_body_oai

    # - Successful response -
    status_code = "ok"

    operation.setdefault("responses", {}).setdefault(status_code, {})[
        "description"
    ] = "Successful response. **result** field:"
    response_schema, _, _ = field_schema(
        route.response_field,
        model_name_map=model_name_map,
        ref_prefix=REF_PREFIX,
    )

    operation.setdefault("responses", {}).setdefault(status_code, {}).setdefault(
        "content",
        {},
    ).setdefault("application/json", {})["schema"] = response_schema

    # - Errors -
    if route.errors:
        operation_errors = operation.setdefault("responses", {})
        for (  # noqa: WPS352
            additional_status_code,
            additional_response,
        ) in route.errors.items():
            process_response: Dict[str, Any] = {}
            status_code_key = str(additional_status_code)
            openapi_response = operation_errors.setdefault(status_code_key, {})

            if route.errors_models and (
                field := route.errors_models[additional_status_code]  # noqa: WPS332
            ):
                additional_field_schema, _, _ = field_schema(
                    field,
                    model_name_map=model_name_map,
                    ref_prefix=REF_PREFIX,
                )
                media_type = "application/json"
                additional_schema = (
                    process_response.setdefault("content", {})
                    .setdefault(media_type, {})
                    .setdefault("schema", {})
                )
                deep_dict_update(additional_schema, additional_field_schema)

            description = additional_response["description"] or "Error"
            deep_dict_update(openapi_response, process_response)
            openapi_response[
                "description"
            ] = f"Reason: *{description}*. **error** object:"

    path["post"] = operation
    return path, definitions
