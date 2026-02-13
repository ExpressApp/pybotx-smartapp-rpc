import inspect
from enum import Enum
from typing import Any, get_args, get_origin

from pydantic import BaseModel, TypeAdapter

from pybotx_smartapp_rpc.models.method import RPCMethod
from pybotx_smartapp_rpc.router import RPCRouter

REF_PREFIX = "#/components/schemas/"


def deep_dict_update(
    destination_dict: dict[Any, Any],
    source_dict: dict[Any, Any],
) -> None:
    for key in source_dict:
        if (
            key in destination_dict
            and isinstance(destination_dict[key], dict)
            and isinstance(source_dict[key], dict)
        ):
            deep_dict_update(destination_dict[key], source_dict[key])
        else:
            destination_dict[key] = source_dict[key]


def _extract_nested_models(
    annotation: Any,
    visited: set[type[BaseModel] | type[Enum]] | None = None,
) -> set[type[BaseModel] | type[Enum]]:
    if visited is None:
        visited = set()

    origin = get_origin(annotation)
    if origin is not None:
        models: set[type[BaseModel] | type[Enum]] = set()
        for arg in get_args(annotation):
            models.update(_extract_nested_models(arg, visited))

        return models

    if not inspect.isclass(annotation):
        return set()

    if issubclass(annotation, BaseModel):
        if annotation in visited:
            return set()

        visited.add(annotation)
        nested_models: set[type[BaseModel] | type[Enum]] = {annotation}
        for field in annotation.model_fields.values():
            nested_models.update(_extract_nested_models(field.annotation, visited))

        return nested_models

    if issubclass(annotation, Enum):
        return {annotation}

    return set()


def get_rpc_flat_models_from_routes(
    router: RPCRouter,
) -> set[type[BaseModel] | type[Enum]]:
    flat_models: set[type[BaseModel] | type[Enum]] = set()
    visited: set[type[BaseModel] | type[Enum]] = set()

    for route in router.rpc_methods.values():
        if not route.include_in_schema:
            continue

        if route.arguments_model:
            flat_models.update(_extract_nested_models(route.arguments_model, visited))

        flat_models.update(_extract_nested_models(route.response_type, visited))
        for error_model in route.errors_models.values():
            flat_models.update(_extract_nested_models(error_model, visited))

    return flat_models


def get_rpc_model_name_map(
    flat_models: set[type[BaseModel] | type[Enum]],
) -> dict[type[BaseModel] | type[Enum], str]:
    model_name_map: dict[type[BaseModel] | type[Enum], str] = {}
    names_counter: dict[str, int] = {}

    for model in sorted(flat_models, key=lambda current_model: current_model.__name__):
        model_name = model.__name__
        index = names_counter.get(model_name, 0)
        names_counter[model_name] = index + 1

        if index:
            model_name = f"{model_name}_{index}"

        model_name_map[model] = model_name

    return model_name_map


def get_rpc_model_definitions(
    *,
    flat_models: set[type[BaseModel] | type[Enum]],
    model_name_map: dict[type[BaseModel] | type[Enum], str],
) -> dict[str, Any]:
    definitions: dict[str, Any] = {}
    for model in flat_models:
        if issubclass(model, BaseModel):
            model_schema = model.model_json_schema(
                ref_template=f"{REF_PREFIX}{{model}}"
            )
        else:
            model_schema = TypeAdapter(model).json_schema(
                ref_template=f"{REF_PREFIX}{{model}}",
            )

        if definitions_map := model_schema.pop("$defs", None):
            definitions.update(definitions_map)

        if description := model_schema.get("description"):
            model_schema["description"] = description.split("\f")[0]

        model_name = model_name_map[model]
        definitions[model_name] = model_schema

    return definitions


def _build_schema_from_type(
    model: Any,
    model_name_map: dict[type[BaseModel] | type[Enum], str],
) -> dict[str, Any]:
    if inspect.isclass(model):
        if issubclass(model, BaseModel) or issubclass(model, Enum):
            return {"$ref": f"{REF_PREFIX}{model_name_map[model]}"}

    schema = TypeAdapter(model).json_schema(ref_template=f"{REF_PREFIX}{{model}}")
    schema.pop("$defs", None)

    return schema


def get_openapi_operation_rpc_args(
    *,
    body_model: type[BaseModel] | None,
    model_name_map: dict[type[BaseModel] | type[Enum], str],
) -> dict[str, Any] | None:
    if body_model is None:
        return None

    body_schema = _build_schema_from_type(
        body_model,
        model_name_map,
    )
    request_media_type = "application/json"
    request_body_oai: dict[str, Any] = {"required": True}

    request_media_content: dict[str, Any] = {"schema": body_schema}
    request_body_oai["content"] = {request_media_type: request_media_content}

    return request_body_oai


def get_openapi_rpc_metadata(*, name: str, route: RPCMethod) -> dict[str, Any]:
    operation: dict[str, Any] = {
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
    model_name_map: dict[type[BaseModel] | type[Enum], str],
    security_scheme: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Taken from FastAPI."""
    path: dict[str, Any] = {}

    operation = get_openapi_rpc_metadata(name=method_name, route=route)

    request_body_oai = get_openapi_operation_rpc_args(
        body_model=route.arguments_model,
        model_name_map=model_name_map,
    )
    if request_body_oai:
        operation["requestBody"] = request_body_oai

    # - Successful response -
    response_schema = _build_schema_from_type(
        route.response_type,
        model_name_map=model_name_map,
    )
    response_schema.setdefault(
        "title",
        f"Response {route.handler.__name__.replace('_', ' ').title()}",
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
        for error_status_code, error_response in route.errors.items():
            process_response: dict[str, Any] = {}
            openapi_response = operation_errors.setdefault(str(error_status_code), {})

            if route.errors_models and (
                error_model := route.errors_models[error_status_code]  # noqa: WPS332
            ):
                error_field_schema = _build_schema_from_type(
                    error_model,
                    model_name_map=model_name_map,
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
