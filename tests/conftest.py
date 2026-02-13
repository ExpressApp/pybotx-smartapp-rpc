from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from pybotx import (
    AttachmentTypes,
    Bot,
    BotAccount,
    Chat,
    ChatTypes,
    Document,
    Image,
    SmartAppEvent,
    UserDevice,
    UserSender,
)


@pytest.fixture
def bot_id() -> UUID:
    return UUID("24348246-6791-4ac0-9d86-b948cd6a0e46")


@pytest.fixture
def ref() -> UUID:
    return UUID("6fafda2c-6505-57a5-a088-25ea5d1d0364")


@pytest.fixture
def chat_id() -> UUID:
    return UUID("dea55ee4-7a9f-5da0-8c73-079f400ee517")


@pytest.fixture
def host() -> str:
    return "cts.example.com"


@pytest.fixture
def smartapp_event_factory(
    bot_id: UUID,
    ref: UUID,
    chat_id: UUID,
    host: str,
) -> Callable[..., SmartAppEvent]:
    def factory(
        method: str,
        *,
            params: dict[str, Any] | None = None,
    ) -> SmartAppEvent:
        smartapp_data: dict[str, Any] = {
            "type": "smartapp_rpc",
            "method": method,
        }
        if params is not None:
            smartapp_data["params"] = params

        return SmartAppEvent(
            ref=ref,
            smartapp_id=bot_id,
            bot=BotAccount(
                id=bot_id,
                host=host,
            ),
            data=smartapp_data,
            opts={},
            smartapp_api_version=1,
            files=[],
            sender=UserSender(
                huid=uuid4(),
                udid=uuid4(),
                ad_login=None,
                ad_domain=None,
                username=None,
                is_chat_admin=True,
                is_chat_creator=True,
                device=UserDevice(
                    manufacturer=None,
                    device_name=None,
                    os=None,
                    pushes=None,
                    timezone=None,
                    permissions=None,
                    platform=None,
                    platform_package_id=None,
                    app_version=None,
                    locale=None,
                ),
            ),
            chat=Chat(
                id=chat_id,
                type=ChatTypes.GROUP_CHAT,
            ),
            raw_command=None,
        )

    return factory


@pytest.fixture
def bot() -> AsyncMock:
    return AsyncMock(spec=Bot)


@pytest.fixture
def document() -> Document:
    return Document(
        type=AttachmentTypes.DOCUMENT,
        filename="pass.txt",
        size=1502345,
        is_async_file=True,
        _file_id=UUID("8dada2c8-67a6-4434-9dec-570d244e78ee"),
        _file_url="https://link.to/file",
        _file_mimetype="plain/text",
        _file_hash="Jd9r+OKpw5y+FSCg1xNTSUkwEo4nCW1Sn1AkotkOpH0=",
    )


@pytest.fixture
def image() -> Image:
    return Image(
        type=AttachmentTypes.IMAGE,
        filename="pass.png",
        size=1502345,
        is_async_file=True,
        _file_id=UUID("8dada2c8-67a6-4434-9dec-570d244e78ee"),
        _file_url="https://link.to/file",
        _file_mimetype="image/png",
        _file_hash="Jd9r+OKpw5y+FSCg1xNTSUkwEo4nCW1Sn1AkotkOpH0=",
    )
