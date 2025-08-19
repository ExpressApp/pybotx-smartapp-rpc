from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, Union

from pydantic import BaseModel, TypeAdapter

from pybotx_smartapp_rpc import RPCRouter
from pybotx_smartapp_rpc.models.method import RPCMethod
from pybotx_smartapp_rpc.models.model_field import ModelField
from pybotx_smartapp_rpc.openapi.utils import (
    deep_dict_update,
    get_flat_models_from_fields,
    get_model_name_map,
    get_schema_or_ref,
)

REF_PREFIX = "#/components/schemas/"
ModelNameMap: type[dict[type[Union[BaseModel | Enum]], str]] = Dict[
    Union[Type[BaseModel], Type[Enum]], str
]


def update_fastapi_paths_by_rpc_router(
    openapi_dict: dict[str, Any],
    rpc_router: RPCRouter,
    security_definitions: Optional[dict[str, Any]] = None,
    operation_security: Optional[dict[str, Any]] = None,
) -> None:
    if security_definitions is not None:
        openapi_dict.setdefault("components", {}).setdefault(
            "securitySchemes", {}
        ).update(security_definitions)

    paths: Dict[str, Dict[str, Any]] = {}

    flat_rpc_models = get_rpc_flat_models_from_routes(rpc_router)
    rpc_model_name_map = get_model_name_map(flat_rpc_models)
    rpc_definitions = get_rpc_model_definitions(
        flat_models=flat_rpc_models, model_name_map=rpc_model_name_map
    )

    for method_name, method in rpc_router.rpc_methods.items():
        if not method.include_in_schema:
            continue

        if path := get_rpc_openapi_path(
            method_name=method_name,
            route=method,
            model_name_map=rpc_model_name_map,
            security_scheme=operation_security,
        ):
            paths.setdefault(f"/{method_name}", {}).update(path)

    if rpc_definitions:
        openapi_dict.setdefault("components", {}).setdefault("schemas", {}).update(
            {k: rpc_definitions[k] for k in sorted(rpc_definitions)}
        )

    openapi_dict.setdefault("paths", {}).update(paths)


def get_rpc_model_definitions(
    *,
    flat_models: set[type[BaseModel | Enum]],
    model_name_map: dict[type[BaseModel | Enum], str],
) -> dict[str, Any]:
    definitions: dict[str, dict[str, Any]] = {}

    for model in flat_models:
        if isinstance(model, type) and issubclass(model, BaseModel):
            m_schema = model.model_json_schema(ref_template=REF_PREFIX + "{model}")
        else:
            m_schema = TypeAdapter(model).json_schema(
                ref_template=REF_PREFIX + "{model}"
            )

        nested_defs = m_schema.pop("$defs", {})
        definitions.update(nested_defs)

        model_name = model_name_map[model]

        # Trim FastAPI-style docstrings if present
        if "description" in m_schema:
            m_schema["description"] = m_schema["description"].split("\f")[0]

        # Register schema under the resolved name
        definitions[model_name] = m_schema

    return definitions


def get_rpc_flat_models_from_routes(
    router: RPCRouter,
) -> Set[Union[Type[BaseModel], Type[Enum]]]:
    body_fields_from_routes: List[ModelField] = []
    responses_from_routes: List[ModelField] = []

    for rpc_method in router.rpc_methods.values():
        if not rpc_method.include_in_schema:
            continue

        if rpc_method.arguments_field:
            body_fields_from_routes.append(
                rpc_method.arguments_field,
            )
        if rpc_method.response_field:
            responses_from_routes.append(rpc_method.response_field)

        if rpc_method.errors_models:
            responses_from_routes.extend(
                rpc_method.errors_models.values(),
            )

    return get_flat_models_from_fields(
        body_fields_from_routes + responses_from_routes,
        known_models=set(),
    )


def get_rpc_openapi_path(
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
    response_schema = get_schema_or_ref(
        route.response_field, model_name_map, REF_PREFIX
    )
    response_schema["title"] = route.response_field.name.replace("_", " ").title()

    operation.setdefault("responses", {}).setdefault(200, {}).update(
        {
            "description": "Successful response. **result** field:",
            "content": {"application/json": {"schema": response_schema}},
        }
    )

    # - Errors -
    if route.errors:
        operation_errors = operation.setdefault("responses", {})
        for error_status_code, error_response in route.errors.items():
            process_response: Dict[str, Any] = {}
            openapi_response = operation_errors.setdefault(str(error_status_code), {})

            if route.errors_models and (
                field := route.errors_models[error_status_code]
            ):
                error_schema = get_schema_or_ref(field, model_name_map, REF_PREFIX)

                process_response.setdefault("content", {}).setdefault(
                    "application/json", {}
                )["schema"] = error_schema

            description = error_response["description"] or "Error"
            deep_dict_update(openapi_response, process_response)
            openapi_response["description"] = f"**Error**: {description}"

    if security_scheme:
        operation.setdefault("security", []).append(security_scheme)

    path["post"] = operation
    return path


def get_openapi_operation_rpc_args(
    *,
    body_field: Optional[ModelField],
    model_name_map: Dict[Union[Type[BaseModel], Type[Enum]], str],
) -> Optional[Dict[str, Any]]:
    if not body_field:
        return None

    body_schema = get_schema_or_ref(body_field, model_name_map, REF_PREFIX)

    request_media_type = "application/json"
    request_body_oai: Dict[str, Any] = {}
    if body_field.required:
        request_body_oai["required"] = True

    request_body_oai["content"] = {request_media_type: {"schema": body_schema}}

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
