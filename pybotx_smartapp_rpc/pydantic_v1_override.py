from enum import Enum
from typing import Union, Sequence, Type

from pydantic.fields import FieldInfo
from pydantic.v1.fields import ModelField
from pydantic.v1.schema import TypeModelSet
from pydantic.v1.utils import lenient_issubclass

from pydantic.v1 import BaseModel as BaseModelV1
from pydantic import BaseModel as BaseModelV2

BaseModelTypes = (BaseModelV1, BaseModelV2)


def _get_field_type(field: Union[ModelField, FieldInfo]):
    """
    Extract the declared type from either a Pydantic v1 ModelField
    or a Pydantic v2 FieldInfo.
    """
    if isinstance(field, ModelField):
        return field.type_
    elif isinstance(field, FieldInfo):
        return field.annotation
    else:
        raise TypeError(f"Unsupported field type: {type(field)}")

def get_flat_models_from_model(model: Type[Union[BaseModelV1, BaseModelV2]],
                               known_models: TypeModelSet) -> TypeModelSet:
    """
    Custom version of pydantic.v1.schema.get_flat_models_from_model
    that supports v2 BaseModel and v2 FieldInfo.
    """
    flat_models: TypeModelSet = set()

    if model in known_models:
        return flat_models

    known_models.add(model)
    flat_models.add(model)

    # v1 stores __fields__, v2 stores model_fields
    fields = getattr(model, '__fields__', None) or getattr(model, 'model_fields', {})
    flat_models |= get_flat_models_from_fields(fields.values(), known_models=known_models)

    return flat_models



def get_flat_models_from_fields(
    fields: Sequence[Union[ModelField, FieldInfo]],
    known_models: TypeModelSet,
) -> TypeModelSet:
    """
    Take a list of fields (v1 ModelField or v2 FieldInfo) and return all BaseModel/Enum types used,
    recursively.
    """
    flat_models: TypeModelSet = set()
    for field in fields:
        flat_models |= get_flat_models_from_field(field, known_models=known_models)
    return flat_models


def get_flat_models_from_field(
    field: Union[ModelField, FieldInfo],
    known_models: TypeModelSet,
) -> TypeModelSet:
    """
    Handle one field (v1 ModelField or v2 FieldInfo) and return all models in its type tree.
    """

    flat_models: TypeModelSet = set()

    field_type = _get_field_type(field)

    # Support TypeAdapter-style wrappers
    if lenient_issubclass(getattr(field_type, '__pydantic_model__', None), BaseModelTypes):
        field_type = field_type.__pydantic_model__

    sub_fields = getattr(field, "sub_fields", None)

    if sub_fields and not lenient_issubclass(field_type, BaseModelTypes):
        flat_models |= get_flat_models_from_fields(sub_fields, known_models=known_models)
    elif lenient_issubclass(field_type, BaseModelTypes) and field_type not in known_models:
        flat_models |= get_flat_models_from_model(field_type, known_models=known_models)
    elif lenient_issubclass(field_type, Enum):
        flat_models.add(field_type)

    return flat_models