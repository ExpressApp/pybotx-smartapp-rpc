from dataclasses import dataclass
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined as Undefined


@dataclass
class ModelField:
    """
    Represents a model field with metadata and utilities for managing its properties.

    The ModelField class encapsulates information about a model's field, including its
    name, type hint, default value, and whether it is required. It provides methods
    and properties to query and manage these attributes effectively.

    :ivar field_info: Metadata and information about the field.
    :ivar name: The name of the field.
    """

    field_info: FieldInfo
    name: str

    @property
    def required(self) -> bool:
        return self.field_info.is_required()

    @property
    def default(self) -> Any:
        return self.get_default()

    @property
    def type_(self) -> Any:
        return self.field_info.annotation

    def get_default(self) -> Any:
        if self.field_info.is_required():
            return Undefined
        return self.field_info.get_default(call_default_factory=True)
