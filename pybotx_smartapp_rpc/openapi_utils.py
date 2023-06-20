from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

from pydantic import BaseModel
from pydantic.fields import ModelField
from pydantic.schema import field_schema, get_flat_models_from_fields

from pybotx_smartapp_rpc import RPCRouter
from pybotx_smartapp_rpc.models.method import RPCMethod

REF_PREFIX = "#/components/schemas/"


def get_rpc_flat_models_from_routes(
    router: RPCRouter,
) -> Set[Union[Type[BaseModel], Type[Enum]]]:
    body_fields_from_routes: List[ModelField] = []
    responses_from_routes: List[ModelField] = []

    for method_name in router.rpc_methods:
        if router.rpc_methods[method_name].arguments_field:
            body_fields_from_routes.append(
                router.rpc_methods[method_name].arguments_field,  # type: ignore
            )
        if router.rpc_methods[method_name].response_field:
            responses_from_routes.append(router.rpc_methods[method_name].response_field)

        # params = get_flat_params(route.dependant)
        # request_fields_from_routes.extend(params)

    flat_models = get_flat_models_from_fields(
        body_fields_from_routes + responses_from_routes,
        known_models=set(),
    )
    return flat_models


def get_openapi_operation_rpc_args(
    *,
    body_field: Optional[ModelField],
    model_name_map: Dict[Union[Type[BaseModel], Type[Enum]], str],
) -> Optional[Dict[str, Any]]:
    if not body_field:
        return None

    assert isinstance(body_field, ModelField)
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
    # operation["tags"] = "RPC"
    operation["summary"] = (
        name.replace(".", " ").replace(":", " ").replace("_", " ").title()
    )
    operation["description"] = route.handler.__doc__
    operation[
        "operationId"
    ] = f"rpc_{name.replace('.', '_').replace(':', '_').replace('_', '_').lower()}"

    if route.tags:
        operation["tags"] = route.tags

    return operation


def get_rpc_openapi_path(
    *,
    method_name: str,
    route: RPCMethod,
    model_name_map: Dict[Union[Type[BaseModel], Type[Enum]], str],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    path = {}
    definitions: Dict[str, Any] = {}
    # if isinstance(route.response_class, DefaultPlaceholder):
    #     current_response_class: Type[Response] = route.response_class.value
    # else:

    operation = get_openapi_rpc_metadata(name=method_name, route=route)

    request_body_oai = get_openapi_operation_rpc_args(
        body_field=route.arguments_field,
        model_name_map=model_name_map,
    )
    if request_body_oai:
        operation["requestBody"] = request_body_oai

    status_code = "200"

    operation.setdefault("responses", {}).setdefault(status_code, {})[
        "description"
    ] = "Success"
    response_schema, _, _ = field_schema(
        route.response_field,
        model_name_map=model_name_map,
        ref_prefix=REF_PREFIX,
    )

    operation.setdefault("responses", {}).setdefault(status_code, {}).setdefault(
        "content",
        {},
    ).setdefault("application/json", {})["schema"] = response_schema
    # TODO: RPCError
    # if route.errors:
    #     operation_errors = operation.setdefault("responses", {})
    #     for error in route.errors:
    #         status_code_key = str(additional_status_code).upper()
    #         if status_code_key == "DEFAULT":
    #             status_code_key = "default"
    #         openapi_response = operation_errors.setdefault(
    #             status_code_key, {}
    #         )
    #         assert isinstance(
    #             process_response, dict
    #         ), "An additional response must be a dict"
    #         field = route.response_fields.get(additional_status_code)
    #         additional_field_schema: Optional[Dict[str, Any]] = None
    #         if field:
    #             additional_field_schema, _, _ = field_schema(
    #                 field, model_name_map=model_name_map, ref_prefix=REF_PREFIX
    #             )
    #             media_type = route_response_media_type or "application/json"
    #             additional_schema = (
    #                 process_response.setdefault("content", {})
    #                 .setdefault(media_type, {})
    #                 .setdefault("schema", {})
    #             )
    #             deep_dict_update(additional_schema, additional_field_schema)
    #         status_text: Optional[str] = status_code_ranges.get(
    #             str(additional_status_code).upper()
    #         ) or http.client.responses.get(int(additional_status_code))
    #         description = (
    #             process_response.get("description")
    #             or openapi_response.get("description")
    #             or status_text
    #             or "Additional Response"
    #         )
    #         deep_dict_update(openapi_response, process_response)
    #         openapi_response["description"] = description

    path["post"] = operation
    return path, definitions
