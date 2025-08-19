"""This module contains utility functions for OpenAPI generation."""
import re
from enum import Enum
from typing import Any, Dict, Sequence, Set, Type, Union

from pydantic import BaseModel, TypeAdapter
from pydantic.fields import FieldInfo

from pybotx_smartapp_rpc.models.model_field import ModelField

TypeModelOrEnum = Union[Type[BaseModel], Type[Enum]]
TypeModelSet = Set[TypeModelOrEnum]



def get_flat_models_from_model(
    model: Type[BaseModel],
    known_models: TypeModelSet,
) -> TypeModelSet:
    """
    Recursively collect BaseModel and Enum types from a model definition.
    """
    if model in known_models:
        return set()

    known_models.add(model)
    flat_models: TypeModelSet = {model}

    for field in model.model_fields.values():
        flat_models |= get_flat_models_from_field(field, known_models)

    return flat_models


def get_flat_models_from_fields(
    fields: Sequence[Union[ModelField, FieldInfo]],
    known_models: TypeModelSet,
) -> TypeModelSet:
    flat_models: TypeModelSet = set()
    for field in fields:
        flat_models |= get_flat_models_from_field(field, known_models)
    return flat_models


def get_flat_models_from_field(
    field: Union[ModelField, FieldInfo],
    known_models: TypeModelSet,
) -> TypeModelSet:
    flat_models: TypeModelSet = set()
    field_type = _get_field_type(field)

    if isinstance(field_type, type):
        if issubclass(field_type, BaseModel):
            flat_models |= get_flat_models_from_model(field_type, known_models)
        elif issubclass(field_type, Enum):
            flat_models.add(field_type)

    return flat_models


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9.\-_]", "_", name)


def get_long_model_name(model: TypeModelOrEnum) -> str:
    return f"{model.__module__}__{model.__qualname__}".replace(".", "__")


def get_model_name_map(unique_models: TypeModelSet) -> dict[TypeModelOrEnum, str]:
    """
    Generate unique schema names, avoiding collisions by using module path.
    """
    name_model_map: dict[str, TypeModelOrEnum] = {}
    conflicting_names: Set[str] = set()

    for model in unique_models:
        model_name = normalize_name(model.__name__)
        if model_name in conflicting_names:
            name_model_map[get_long_model_name(model)] = model
        elif model_name in name_model_map:
            conflicting_names.add(model_name)
            other = name_model_map.pop(model_name)
            name_model_map[get_long_model_name(other)] = other
            name_model_map[get_long_model_name(model)] = model
        else:
            name_model_map[model_name] = model

    return {v: k for k, v in name_model_map.items()}


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


def get_schema_or_ref(
    model: ModelField,
    model_name_map: dict[type[Union[BaseModel, Enum]], str],
    ref_prefix: str,
) -> dict:
    if model_name := model_name_map.get(model.type_):
        return {"$ref": ref_prefix + model_name}

    return TypeAdapter(model.type_).json_schema(ref_template=ref_prefix + "{model}")

def _get_field_type(field: Union[ModelField, FieldInfo]) -> Any:
    """Extract declared type from our wrapper or a native FieldInfo."""
    if isinstance(field, ModelField):
        return field.type_
    elif isinstance(field, FieldInfo):
        return field.annotation
    else:
        raise TypeError(f"Unsupported field type: {type(field)}")