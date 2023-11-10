from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, Union

from pydantic import BaseModel
from pydantic.fields import ModelField
from pydantic.schema import (
    field_schema,
    get_flat_models_from_fields,
    model_process_schema,
)

from pybotx_smartapp_rpc import RPCRouter
from pybotx_smartapp_rpc.models.method import RPCMethod

REF_PREFIX = "#/components/schemas/"


def deep_dict_update(
    destination_dict: Dict[Any, Any],
    source_dict: Dict[Any, Any],
) -> None:
    for key in source_dict.keys():
        if (
            key in destination_dict
            and isinstance(destination_dict[key], dict)
            and isinstance(source_dict[key], dict)
        ):
            deep_dict_update(destination_dict[key], source_dict[key])
        else:
            destination_dict[key] = source_dict[key]


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


def get_rpc_model_definitions(
    *,
    flat_models: Set[Union[Type[BaseModel], Type[Enum]]],
    model_name_map: Dict[Union[Type[BaseModel], Type[Enum]], str],
) -> Dict[str, Any]:
    definitions: Dict[str, Dict[str, Any]] = {}
    for model in flat_models:
        m_schema, m_definitions, m_nested_models = model_process_schema(
            model,
            model_name_map=model_name_map,
            ref_prefix=REF_PREFIX,
        )
        definitions.update(m_definitions)
        model_name = model_name_map[model]
        if "description" in m_schema:
            m_schema["description"] = m_schema["description"].split("\f")[0]
        definitions[model_name] = m_schema
    return definitions


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
    operation: Dict[str, Any] = {
        "summary": route.handler.__name__.replace(".", " ").replace("_", " ").title(),
        "description": route.handler.__doc__,
        "operationId": (
            f"rpc_{name.replace('.', '_').replace(':', '_').replace('-', '_').lower()}"
        ),
    }

    if route.tags:
        operation["tags"] = route.tags

    return operation


def get_rpc_openapi_path(  # noqa: WPS231
    *,
    method_name: str,
    route: RPCMethod,
    model_name_map: Dict[Union[Type[BaseModel], Type[Enum]], str],
    security_scheme: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Taken from FastAPI."""
    path = {}

    operation = get_openapi_rpc_metadata(name=method_name, route=route)

    request_body_oai = get_openapi_operation_rpc_args(
        body_field=route.arguments_field,
        model_name_map=model_name_map,
    )
    if request_body_oai:
        operation["requestBody"] = request_body_oai

    # - Successful response -
    response_schema, _, _ = field_schema(
        route.response_field,
        model_name_map=model_name_map,
        ref_prefix=REF_PREFIX,
    )

    operation.setdefault("responses", {}).setdefault("ok", {}).update(
        {
            "description": "Successful response. **result** field:",
            "content": {"application/json": {"schema": response_schema}},
        }
    )

    # - Errors -
    if route.errors:
        operation_errors = operation.setdefault("responses", {})
        for (error_status_code, error_response) in route.errors.items():
            process_response: Dict[str, Any] = {}
            openapi_response = operation_errors.setdefault(str(error_status_code), {})

            if route.errors_models and (
                field := route.errors_models[error_status_code]  # noqa: WPS332
            ):
                error_field_schema, _, _ = field_schema(
                    field,
                    model_name_map=model_name_map,
                    ref_prefix=REF_PREFIX,
                )
                error_schema = (
                    process_response.setdefault("content", {})
                    .setdefault("application/json", {})
                    .setdefault("schema", {})
                )
                deep_dict_update(error_schema, error_field_schema)

            description = error_response["description"] or "Error"
            deep_dict_update(openapi_response, process_response)
            openapi_response["description"] = f"**Error**: {description}"

    if security_scheme:
        operation.setdefault("security", []).append(security_scheme)

    path["post"] = operation
    return path
