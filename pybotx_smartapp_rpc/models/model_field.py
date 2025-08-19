from dataclasses import dataclass
from typing import Annotated, Any

from pydantic import TypeAdapter
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined as Undefined


@dataclass
class ModelField:
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
