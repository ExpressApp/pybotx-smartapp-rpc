import re
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.security import APIKeyHeader
from fastapi.security.base import SecurityBase
from pydantic import BaseModel, ValidationError
from starlette.requests import Request
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN


def get_openapi_security_definitions(
    security_component: SecurityBase,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Get the security definitions and operation security for a security component."""
    security_definition = jsonable_encoder(
        security_component.model,
        by_alias=True,
        exclude_none=True,
    )
    security_name = security_component.scheme_name
    security_definitions = {security_name: security_definition}
    operation_security = {security_name: []}  # type: ignore
    return security_definitions, operation_security


DOCS = """Установка параметров для выполнение RPC методов.

* `bot_id` - huid бота. Необязательное поле.
* `sender_huid` - huid пользователя. Необязательное поле.
* `sender_udid` - udid пользователя. Необязательное поле.
* `chat_id` - id чата. Необязательное поле.

**Example**: `bot_id=UUID&sender_huid=UUID&sender_udid=UUID&chat_id=UUID`"""


class RPCAuthConfig(BaseModel):
    bot_id: UUID
    sender_huid: UUID = uuid4()
    sender_udid: UUID = uuid4()
    chat_id: UUID = uuid4()


class RPCAuth(APIKeyHeader):
    PATTERN = "([^?=&]+)=([^&]*)"

    def __init__(
        self,
        *,
        bot_id: UUID,
        scheme_name: str = "RPC Auth",
        name: str = "X-RPC-AUTH",
        description: str = DOCS,
        **kwargs: Any,
    ) -> None:
        self.bot_id = bot_id
        super().__init__(
            scheme_name=scheme_name, name=name, description=description, **kwargs
        )

    async def __call__(self, request: Request) -> RPCAuthConfig:  # type: ignore
        api_key = request.headers.get(self.model.name)
        if not api_key:
            return RPCAuthConfig(bot_id=self.bot_id)

        params = re.findall(self.PATTERN, api_key)
        if not params:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Invalid RPC Auth format"
            )
        try:
            params_dict = dict(params)
            if "bot_id" not in params_dict:
                params_dict["bot_id"] = self.bot_id

            config = RPCAuthConfig(**params_dict)
        except ValidationError as ex:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail=str(ex)
            ) from None

        return config
